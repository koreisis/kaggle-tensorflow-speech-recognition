TRAIN_AUDIO_PATH = "input/train/audio"
TRAIN_PATH = "input/train"
TRAIN_FILE_META_INFO = "data/train_file_info.csv"
POSSIBLE_LABELS = ['yes',
                   'no',
                   'up',
                   'down',
                   'left',
                   'right',
                   'on',
                   'off',
                   'stop',
                   'go',
                   'silence',
                   'unknown']
TEST_AUDIO_PATH = "input/test/audio"
SILECE_DATA_PATH = "data/silence"

BATCH_SIZE = 64

SAMPLE_RATE = 16000

VOLUME_UP = 1.2
VOLUME_DOWN = 0.8
SHIFT_MAX = int(SAMPLE_RATE*0.2)
SHIFT_MIN = int(SAMPLE_RATE*0.1)
SPEED_MAX = 0.3
SPEED_MIN = 0.1
PITCH_MAX = 4
PITCH_MIN = 3
ADD_WN_MIN = 0.005
ADD_WN_MAX = 0.01
MIX_BGN_RATE = 0.3
MIX_BGN_MAX = 0.5
LP_MIN = 2000
LP_MAX = 7999

AUG_LIST = []
# AUG_LIST = ["speed_down",
#             "speed_up",
#             "shift_forward",
#             "shift_backward",
#             "pitch_up",
#             "mix_random",
#             "add_wn"]
AUG_VERSION = "2017_12_25_00_55_41"
AUG_PATH = "data/augment/"
