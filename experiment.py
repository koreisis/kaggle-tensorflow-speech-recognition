from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score
from tqdm import tqdm
import config
import generator
import learner
import model
import utils
import submit

"""
Experiment and Cross Validation Script for local data.

Todo:
1. Validation silence data (completed)
2. Cross Vaidation script with respect of uid split
"""


def extract_fname(path, silence):
    p = Path(path)
    if silence:
        return p.parts[-1]
    else:
        return p.parts[-2] + '/' + p.parts[-1]


def sample_rows(df, sample_size):
    grouped = df.groupby('plnum')
    df = grouped.apply(lambda x: x.sample(n=sample_size))
    return df


def augment_data_load(paths, augs, version, silence=False):

    def extract_fn(x):
        return extract_fname(x, silence)

    flist = paths.path.apply(extract_fn)
    print(len(flist))
    
    for aug in tqdm(augs, desc='Aug data import'):
        # print("load file info of {}".format(aug))
        aug_path = "{}_file_info_version_{}.csv".format(aug,
                                                        version)
        augment_file_info = pd.read_csv(Path("data/")/aug_path)
        augment_file_info = augment_file_info[["path",
                                               "uid",
                                               "possible_label",
                                               "plnum",
                                               "is_valid"]]
        augment_file_info["fn"] = augment_file_info.path.apply(extract_fn)
        augment_file_info = augment_file_info[augment_file_info.fn.isin(flist)]
        augment_file_info = augment_file_info.drop("fn", axis=1)
        # print(augment_file_info.shape)        
        paths = pd.concat([paths, augment_file_info])

    print(paths.shape)
    return paths


def data_load(silence_data_version):
    print("base data load")
    file_df = pd.read_csv(config.TRAIN_FILE_META_INFO)
    file_df = file_df[["path", "uid", "possible_label", "plnum", "is_valid"]]
    bg_paths = file_df[file_df["possible_label"] == "_background_noise_"]
    file_df = file_df[file_df["possible_label"] != "_background_noise_"]
    file_df['plnum'] = file_df.plnum.astype('int64')

    silence_data_path = Path(config.SILENCE_DATA_PATH)/silence_data_version
    silence_df = pd.read_csv(silence_data_path/"file_info.csv")
    print("done")

    return file_df, bg_paths, silence_df


def experiment(estimator,
               train_df,
               valid_df,
               bg_paths,
               batch_size,
               sample_size,
               augment_list,
               version_path=None,
               csv_log_path=None):
    
    label_num = len(config.POSSIBLE_LABELS)
    train_generator = generator.batch_generator(train_df,
                                                batch_size,
                                                label_num)
    valid_generator = generator.batch_generator(valid_df,
                                                batch_size,
                                                label_num,
                                                mode='valid')
    data_size = sample_size*label_num
    valid_steps = int(np.ceil(valid_df.shape[0]/batch_size))
    steps_per_epoch = int(np.ceil(data_size/batch_size))

    learn = learner.Learner(estimator, version_path, csv_log_path)
    result = learn.learn(train_generator,
                         valid_generator,
                         valid_steps,
                         steps_per_epoch=steps_per_epoch)
    return result


def validation(silence_data_version,
               estimator,
               augment_list,
               aug_version,
               sample_size=2000,
               batch_size=config.BATCH_SIZE,
               silence_train_size=2000):
    print("experiment(validation type) start")

    version_path = Path("model")/estimator.name/utils.now()
    version_path.mkdir(parents=True, exist_ok=True)
    
    file_df, bg_paths, silence_df = data_load(silence_data_version)

    train_df = file_df[~file_df.is_valid]
    train_df = sample_rows(train_df, sample_size)
    valid_df = file_df[file_df.is_valid]
    valid_df = sample_rows(valid_df, 200)

    print(len(train_df), len(valid_df))
    assert(set(train_df.uid) & set(valid_df.uid) == set())

    silence_train = silence_df.iloc[:silence_train_size]
    silence_valid = silence_df.iloc[silence_train_size:silence_train_size+200]

    print("load augmentation")
    print("train")
    train_df = augment_data_load(train_df, augment_list, aug_version)
    print("valid")
    valid_df = augment_data_load(valid_df, augment_list, aug_version)
    print("silence_data")
    silence_train = augment_data_load(silence_train, augment_list, aug_version,
                                      silence=True)
    silence_valid = augment_data_load(silence_valid, augment_list, aug_version,
                                      silence=True)
    print("done")

    train_df = pd.concat([train_df, silence_train])
    valid_df = pd.concat([valid_df, silence_valid])
    sample_size = sample_size*(len(augment_list) + 1)

    assert(len(train_df.plnum.unique()) == len(config.POSSIBLE_LABELS))

    print("data load done")
    estimator.model_init()
    struct_json = estimator.model.to_json()
    with open(version_path/"model.json", "w") as fp:
        fp.write(struct_json)
    
    result = experiment(estimator, train_df, valid_df, bg_paths,
                        batch_size, sample_size, augment_list,
                        version_path=str(version_path/"weights.hdf5"),
                        csv_log_path=str(version_path/"epoch_log.csv"))
    predict_valid_probs = submit.predict(valid_df,
                                         bg_paths,
                                         estimator)
    valid_plobs = pd.DataFrame(predict_valid_probs,
                               columns=config.POSSIBLE_LABELS)
    valid_df.index = range(len(valid_df))
    valid_plobs_df = pd.concat([valid_df, valid_plobs], axis=1)

    valid_plobs_df.to_csv(version_path/"valid_probs.csv",
                          index=False)
    
    return result


def cross_validation(estimator_name,
                     silence_data_version,
                     cv_version,
                     aug_version,
                     aug_list,
                     n_splits=5,
                     base_valid_split=0.9,
                     base_sample_size=1600,
                     base_valid_size=50,
                     base_test_size=200,
                     batch_size=config.BATCH_SIZE,
                     silence_train_size=1800):
    
    """cross_validation func with silence_data
    
    Todo: uid label list encoding -> stratified kfold
    """

    version_path = Path("cv/")/estimator_name/cv_version
    version_path.mkdir(parents=True, exist_ok=True)
    file_df, bg_paths, silence_data = data_load(silence_data_version)
    file_df = file_df.drop(["is_valid"], axis=1)

    uid_list = file_df.uid.unique()
    kfold_data = KFold(n_splits=n_splits, shuffle=True).split(uid_list)
    kfold_silence = KFold(n_splits=n_splits, shuffle=True).split(silence_data)
    kfold = zip(kfold_data, kfold_silence)
    result = list()
    cv_acc = list()

    for i, ((train_id, other_id), (train_sid, other_sid)) in enumerate(kfold):
        print("fold {} start".format(i))
        print("-"*80)
        id_valid_len = int(len(train_id)*base_valid_split)
        train_uid = uid_list[train_id[:id_valid_len]]
        valid_uid = uid_list[train_id[id_valid_len:]]
        test_uid = uid_list[other_id]

        train = file_df[file_df.uid.isin(train_uid)]
        train = sample_rows(train, base_sample_size)
        valid = file_df[file_df.uid.isin(valid_uid)]
        valid = sample_rows(valid, base_valid_size)
        test = file_df[file_df.uid.isin(test_uid)]
        # test = sample_rows(test, base_test_size)

        # quick check for proper validation
        assert(set(train.uid) & set(valid.uid) == set())
        assert(set(train.uid) & set(test.uid) == set())
        assert(set(valid.uid) & set(test.uid) == set())

        train = augment_data_load(train, config.AUG_LIST, aug_version)
        sid_valid_len = int(len(train_sid)*base_valid_split)
        silence_train = silence_data.iloc[train_sid[:sid_valid_len]]
        silence_train = sample_rows(silence_train, base_sample_size)
        silence_train = augment_data_load(silence_train,
                                          config.AUG_LIST,
                                          aug_version,
                                          silence=True)
        train = pd.concat([train, silence_train])

        valid = augment_data_load(valid, config.AUG_LIST, aug_version)
        silence_valid = silence_data.iloc[train_sid[sid_valid_len:]]
        silence_valid = sample_rows(silence_valid, base_valid_size)
        silence_valid = augment_data_load(silence_valid,
                                          config.AUG_LIST,
                                          aug_version,
                                          silence=True)
        valid = pd.concat([valid, silence_valid])

        test = augment_data_load(test, config.AUG_LIST, aug_version)
        test_silence_id = other_sid
        silence_test = silence_data.iloc[test_silence_id]
        # silence_test = sample_rows(silence_test, base_test_size)
        silence_test = augment_data_load(silence_test,
                                         config.AUG_LIST,
                                         aug_version,
                                         silence=True)
        test = pd.concat([test, silence_test])

        # info of dataset
        print('{:>10},{:>10},{:>10},{:>10}'.format("type",
                                                   "train_size",
                                                   "valid_size",
                                                   "test_size"))
        print('train', len(train), len(valid), len(test))
        print('silence',
              len(silence_train),
              len(silence_valid),
              len(silence_test))
        print("train label dist")
        print(train.possible_label.value_counts())
        print("valid label dist")
        print(valid.possible_label.value_counts())
        print("test label dist")
        print(test.possible_label.value_counts())

        sample_size = base_sample_size*(len(aug_list) + 1)
        print('augmentation types', len(aug_list), sample_size)

        label_dist = train.possible_label.value_counts()
        label_dist.to_csv(version_path/"fold_{}_train_ldist".format(i))

        label_dist = test.possible_label.value_counts()
        label_dist.to_csv(version_path/"fold_{}_test_ldist".format(i))
        
        fold_dump_path = str(version_path / "fold_{}.hdf5".format(i))
        csv_log_path = str(version_path / "fold_{}_log.csv".format(i))

        # TODO: refactor architecture of model module (VGG1D, STFTCNN)
        if estimator_name == "VGG1D":
            estimator = model.VGG1D()
            estimator.model_init()
        if estimator_name == "VGG1Dv2":
            estimator = model.VGG1Dv2()
            estimator.model_init()
        if estimator_name == "STFTCNN":
            estimator = model.STFTCNN()
            estimator.model_init()

        print("learning start")
        print("-"*40)
        res_fold = experiment(estimator, train, valid, bg_paths,
                              batch_size, sample_size, aug_list,
                              version_path=fold_dump_path,
                              csv_log_path=csv_log_path)
        print("-"*40)
        print("done")

        predict_test_probs = submit.predict(test,
                                            bg_paths,
                                            estimator)
        fold_plobs = pd.DataFrame(predict_test_probs,
                                  columns=config.POSSIBLE_LABELS)
        test.index = range(len(test))
        fold_plobs_df = pd.concat([test, fold_plobs], axis=1)
        fold_plobs_df.to_csv(version_path/"fold_{}_test.csv".format(i),
                             index=False)
        predict_id = np.argmax(predict_test_probs, axis=1)
        acc = accuracy_score(test.plnum, predict_id)
        print("test accuracy:", acc)

        result.append(res_fold)
        cv_acc.append(acc)

    cv_acc = pd.Series(cv_acc)
    print("cv accuracy mean: {}, std:{}".format(cv_acc.mean(),
                                                cv_acc.std()))
    cv_acc.to_csv(version_path/"cv_test.csv")
    return result


if __name__ == "__main__":
    seed = 2017
    utils.set_seed(seed)

    cv_version = "{time}_{model}_{seed}_augmented".format(**{'time': utils.now(),
                                                             'model': "STFTCNN",
                                                             'seed': seed})
    cnn = model.STFTCNN()
    # validation(config.SILENCE_DATA_VERSION,
    #            cnn,
    #            config.AUG_LIST,
    #            config.AUG_VERSION,
    #            sample_size=2000)
    res = cross_validation("STFTCNN",
                           config.SILENCE_DATA_VERSION,
                           cv_version,
                           config.AUG_VERSION,
                           config.AUG_LIST)
