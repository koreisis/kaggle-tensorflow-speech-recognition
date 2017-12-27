import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import soundfile as sf
import config
import utils
import generator


def silence_data_load():
    file_df = pd.read_csv(config.TRAIN_FILE_META_INFO)
    silence_df = file_df[file_df.possible_label == "_background_noise_"]
    return silence_df


if __name__ == "__main__":
    utils.set_seed(2017)
    
    silence_df = silence_data_load()
    
    version = utils.now()
    size = 4000
    dir_path = Path("data/silence/{}".format(version))
    dir_path.mkdir(exist_ok=True, parents=True)

    for path in silence_df.path:
        print(path)
        silence_data = generator.read_wav_file(path)[1]
        length = config.SAMPLE_RATE
        path_list = []
        bg_type = str(Path(path).parts[-1]).replace(".wav", "")
        for i in range(size):
            path_list.append(dir_path/"{}_{}.wav".format(bg_type, i))
        uid_list = [bg_type for _ in range(size)]
        possible_label_list = ["silence" for _ in range(size)]
        plnum_list = [10 for _ in range(size)]

        res = []
    
        for i in tqdm(range(size)):
            if i % 1000 == 0:
                wav = np.zeros(length)
            else:
                start = np.random.randint(0, len(silence_data) - length)
                if i % 10 == 0:
                    volume = 1
                else:
                    volume = np.random.random()
                wav = silence_data[start:start+length]
                wav = volume*wav
                sf.write(str(path_list[i]),
                         wav,
                         config.SAMPLE_RATE,
                         subtype='PCM_16')

        file_info = {"path": path_list,
                     "possible_label": possible_label_list,
                     "uid": uid_list,
                     "plnum": plnum_list}
        res.append(pd.DataFrame(file_info))

    pd.concat(res).to_csv(dir_path/"file_info.csv")
