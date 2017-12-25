from tensorflow.python.keras.models import Model
from tensorflow.python.keras.layers import Input, Conv2D, MaxPooling2D
from tensorflow.python.keras.layers import Conv1D, MaxPooling1D, LeakyReLU
from tensorflow.python.keras.layers import Activation, BatchNormalization
from tensorflow.python.keras.layers import GlobalAveragePooling2D
from tensorflow.python.keras.layers import GlobalAveragePooling1D, PReLU
from tensorflow.python.keras.layers import GlobalMaxPool2D, GlobalMaxPool1D
from tensorflow.python.keras.layers import concatenate, Dense, Dropout
import config


class STFTCNN():

    def __init__(self,
                 name="STFTCNN"):

        self.name = name

    def model_init(self, input_shape=(257, 98, 2)):
        
        x_in = Input(shape=input_shape)
        x = BatchNormalization()(x_in)
        for i in range(4):
            x = Conv2D(16*(2 ** i), (3, 3))(x)
            x = Activation('elu')(x)
            x = BatchNormalization()(x)
            x = MaxPooling2D((2, 2))(x)
        x = Conv2D(128, (1, 1))(x)
        x_branch_1 = GlobalAveragePooling2D()(x)
        x_branch_2 = GlobalMaxPool2D()(x)
        x = concatenate([x_branch_1, x_branch_2])
        x = Dense(256, activation='relu')(x)
        x = Dropout(0.5)(x)
        x = Dense(len(config.POSSIBLE_LABELS), activation='softmax')(x)
        model = Model(inputs=x_in, outputs=x)
        model.compile(optimizer='nadam',
                      loss='categorical_crossentropy',
                      metrics=['accuracy'])

        self.model = model


class VGG1D():
    """1d VGG16 like convolution model
    """
    def __init__(self, name="VGG1D"):
        self.name = name

    def model_init(self, input_shape=(config.SAMPLE_RATE, 1)):
        x_in = Input(shape=input_shape)
        x = BatchNormalization()(x_in)
        for i in range(6):
            x = Conv1D(8*(2 ** i), 4,
                       strides=2,
                       padding="same")(x)
            x = Activation("relu")(x)
            x = BatchNormalization()(x)
            x = MaxPooling1D(2, padding="same")(x)
        x_branch_1 = GlobalAveragePooling1D()(x)
        x_branch_2 = GlobalMaxPool1D()(x)
        x = concatenate([x_branch_1, x_branch_2])
        x = Dense(1024, activation='relu')(x)
        x = Dropout(0.2)(x)
        x = Dense(len(config.POSSIBLE_LABELS), activation='softmax')(x)
        model = Model(inputs=x_in, outputs=x)
        model.compile(optimizer='rmsprop',
                      loss='categorical_crossentropy',
                      metrics=['accuracy'])

        self.model = model


class Dilated1D():
    """1d dilated convolution model
    """
    def __init__(self, name="Dilated1D"):
        self.name = name

    def model_init(self, input_shape=(config.SAMPLE_RATE, 1)):
        x_in = Input(shape=input_shape)
        x = BatchNormalization()(x_in)
        for i in range(6):
            x = Conv1D(8*(2 ** i), 16,
                       strides=2,
                       padding="same")(x)
            x = PReLU()(x)
            # x = Activation("relu")(x)
            x = BatchNormalization()(x)
            x = MaxPooling1D(2, padding="same")(x)
        x_branch_1 = GlobalAveragePooling1D()(x)
        x_branch_2 = GlobalMaxPool1D()(x)
        x = concatenate([x_branch_1, x_branch_2])
        x = Dense(1024, activation='relu')(x)
        x = Dropout(0.2)(x)
        x = Dense(len(config.POSSIBLE_LABELS), activation='softmax')(x)
        model = Model(inputs=x_in, outputs=x)
        model.compile(optimizer='rmsprop',
                      loss='categorical_crossentropy',
                      metrics=['accuracy'])

        self.model = model

