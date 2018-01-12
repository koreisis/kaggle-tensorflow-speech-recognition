from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm
import config
import utils


def ensembler(sub_list, sub_name):

    test_paths = Path(config.TEST_AUDIO_PATH).glob("*wav")
    test_paths = sorted([Path(path).parts[-1] for path in test_paths])
    test_paths = pd.Series(test_paths, name='fname')
    
    probs = []
    
    for sub in tqdm(sub_list):
        prob_paths = sorted(Path(sub).glob("*.csv"))
        for fold_probs in tqdm(prob_paths):
            fold_prob = pd.read_csv(fold_probs)
            fold_prob = fold_prob.sort_values(by="path")
            assert(all(test_paths.values == fold_prob.path.values))
            probs.append(fold_prob.drop("path", axis=1).values)

    ensembled_probs = np.array(probs).mean(0)
    sub_probs = pd.DataFrame(ensembled_probs, columns=config.POSSIBLE_LABELS)
    sub_probs = pd.concat([test_paths, sub_probs], axis=1)
    sub_probs.to_csv("result/probs/{}.csv".format(sub_name),
                     index=False)
    
    ensemble_plnum = np.argmax(ensembled_probs, axis=1)
    ensemble_plnum = pd.Series(ensemble_plnum, name='label')
    ensemble_label = utils.id_to_label(ensemble_plnum)

    submission = pd.concat([test_paths, ensemble_label], axis=1)
    submission.to_csv("submit/{}.csv".format(sub_name),
                      index=False)


if __name__ == "__main__":

    sub_list = ["sub/VGG1Dv2/2018_01_08_19_37_23_VGG1Dv3_4017_2018_01_09_01_37_49",
                "sub/VGG1Dv2/2018_01_10_01_27_39_VGG1Dv2_4017_2018_01_10_14_47_56",
                "sub/VGG1Dv2/2018_01_09_19_22_27_VGG1Dv3_2017_2018_01_09_22_59_16",
                "sub/VGG1Dv2/2018_01_10_22_50_50_VGG1Dv2_3018_online_2018_01_11_09_26_40",
                "sub/STFTCNNv2/2018_01_12_01_39_43_STFTCNNv2_5017_2018_01_12_18_06_39",
                "sub/STFTCNNv2/2018_01_11_09_54_57_STFTCNNv2_3018_online_2018_01_12_02_48_47",
                "sub/STFTCNN/2018_01_07_05_16_53",
                "sub/STFTCNNv2/2018_01_11_09_54_57_STFTCNNv2_3018_online_2018_01_12_02_48_47"]
    sub_name = utils.now()
    ensembler(sub_list, sub_name)
