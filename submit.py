from pathlib import Path
import numpy as np
import pandas as pd
import generator
import config
import model
import utils


def test_data_load():
    file_df = pd.read_csv(config.TRAIN_FILE_META_INFO)
    df = file_df[["path", "uid", "possible_label", "plnum"]]
    silence_paths = df[df["possible_label"] == "_background_noise_"]
    
    test_paths = Path(config.TEST_AUDIO_PATH).glob("*wav")
    test_paths = pd.DataFrame(test_paths, columns=["path"])
    return test_paths, silence_paths


def predict(test_paths, silence_paths, estimator):
    batch_size = 64
    test_generator = generator.batch_generator(test_paths,
                                               batch_size,
                                               len(config.POSSIBLE_LABELS),
                                               silence_paths,
                                               mode='test')

    steps = int(np.ceil(len(test_paths)/batch_size))
    predict_probs = estimator.model.predict_generator(test_generator, steps)
    return predict_probs


def ensemble(estimator, cv_path, test_paths, silence_paths, sub_path):
    cv_models = Path(cv_path).glob("*.hdf5")
    ensemble_probas = list()
    
    for i, estimator_weight_path in enumerate(cv_models):
        print("fold {} predict".format(i))
        estimator.model.load_weights(estimator_weight_path)
        predict_probs = predict(test_paths, silence_paths, estimator)
        ensemble_probas.append(predict_probs)
        print("done")

    return ensemble_probas


if __name__ == '__main__':

    utils.set_seed(2017)
    version = utils.now()
    id2name = dict(zip(range(len(config.POSSIBLE_LABELS)),
                       config.POSSIBLE_LABELS))
    
    cnn = model.STFTCNN()
    cnn.model_init()
    test_paths, silence_paths = test_data_load()
    cv_version = "2017_12_27_16_17_09_VGG1D_augmented"
    
    cv_path = "cv/{}/{}".format(cnn.name, cv_version)
    sub_path = Path("sub/{}".format(cnn.name))/version
    sub_path.mkdir(parents=True, exist_ok=True)

    print("ensemble start")
    ensemble_probs = ensemble(cnn,
                              cv_path,
                              test_paths,
                              silence_paths,
                              sub_path)
    print("done")
    
    test_fname = test_paths["path"].apply(lambda x: Path(x).parts[-1])

    print("dump cv probs")
    for fold, probs in enumerate(ensemble_probs):
        print("fold {}".format(fold))
        sub_fold_plobs = pd.DataFrame(probs,
                                      columns=config.POSSIBLE_LABELS)
        sub_fold_plobs_df = pd.concat([test_fname, sub_fold_plobs], axis=1)
        sub_fold_plobs_df.to_csv(sub_path/"{}_probs.csv".format(fold),
                                 index=False)

    predict_probs = np.array(ensemble_probs).mean(axis=0)
    predict_cls = np.argmax(predict_probs, axis=1)

    submission = dict()

    print("make submission")
    for i in range(len(test_paths)):
        fname = Path(test_paths.iloc[i][0]).parts[-1]
        label = id2name[predict_cls[i]]
        submission[fname] = label

    with open('submit/{}.csv'.format(version), 'w') as fout:
        fout.write('fname,label\n')
        for fname, label in submission.items():
            fout.write('{},{}\n'.format(fname, label))

    print("done")
