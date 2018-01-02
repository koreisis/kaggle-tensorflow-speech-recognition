from pathlib import Path
import pandas as pd
import numpy as np
import utils
import config


def make_pseudo_labeling(cv_version, fname, threshold=0.9,
                         num_fold=5):
    pseudo_dir = Path('data/pseudo_label/{}'.format(cv_version))
    pseudo_dir.mkdir(exist_ok=True, parents=True)
    
    test_paths = Path(config.TEST_AUDIO_PATH).glob("*wav")
    test_paths = pd.DataFrame(test_paths, columns=["path"])
    test_flist = test_paths.path.apply(lambda x: x.parts[-1])

    for i in range(num_fold):
        pseudo_fold_dir = pseudo_dir/"fold_{}".format(i)
        pseudo_fold_dir.mkdir(parents=True)
        cv_res = []
    
        for j in range(num_fold):
            if i != j:
                res = pd.read_csv("sub/{}/{}_probs.csv".format(cv_version,
                                                                  i))
                assert(test_flist == res.path)
                cv_res.append(res.iloc[-12:])

        cv_probs = np.array(cv_res)
        cv_mean = np.mean(cv_probs, axis=0)
        pseudo_plnum = pd.Series(np.argmax(cv_mean, axis=1), name="plnum")
        max_probs = pd.Series(np.max(cv_mean, axis=1), name="max_probs")
        pseudo_label = pd.concat([test_paths, pseudo_plnum, max_probs], axis=1)
        pseudo_label["label"] = utils.id_to_label(pseudo_label)
        pseudo_label.to_csv(pseudo_fold_dir/fname)

