# -*- coding: utf-8 -*-
"""
Created on Fri Nov 10 05:57:47 2017

@author: fishboi
"""

from keras.optimizers import rmsprop

from keras.models import Model
from keras.layers import Dense, Flatten, Convolution2D, MaxPooling2D, AveragePooling2D, Input, merge

from serpent.machine_learning.reinforcement_learning.ddqn import DDQN

class BDQN(DDQN):
    
    def __init__(
        self,
        input_shape=None,
        input_mapping=None,
        replay_memory_size=10000,
        batch_size=32,
        action_space=None,
        max_steps=1000000,
        observe_steps=None,
        initial_epsilon=1.0,
        final_epsilon=0.1,
        gamma=0.99,
        model_file_path=None,
        model_learning_rate=1e-4,
        override_epsilon=False
    ):
        super().__init__(
            input_shape=input_shape,
            input_mapping=input_mapping,
            replay_memory_size=replay_memory_size,
            batch_size=batch_size,
            action_space=action_space,
            max_steps=max_steps,
            observe_steps=observe_steps,
            initial_epsilon=initial_epsilon,
            final_epsilon=final_epsilon,
            gamma=gamma,
            model_file_path=None,
            model_learning_rate=model_learning_rate,
            override_epsilon=override_epsilon
        )
        
    def _initialize_model(self):
        
        input_layer = Input(shape=self.input_shape)

        tower_1 = Convolution2D(16, 1, 1, border_mode="same", activation="elu")(input_layer)
        tower_1 = Convolution2D(16, 3, 3, border_mode="same", activation="elu")(tower_1)

        tower_2 = Convolution2D(16, 1, 1, border_mode="same", activation="elu")(input_layer)
        tower_2 = Convolution2D(16, 3, 3, border_mode="same", activation="elu")(tower_2)
        tower_2 = Convolution2D(16, 3, 3, border_mode="same", activation="elu")(tower_2)

        tower_3 = MaxPooling2D((3, 3), strides=(1, 1), border_mode="same")(input_layer)
        tower_3 = Convolution2D(16, 1, 1, border_mode="same", activation="elu")(tower_3)

        merged_layer = merge([tower_1, tower_2, tower_3], mode="concat", concat_axis=1)

        output = Flatten()(merged_layer)
        output = Dense(self.action_count)(output)

        model = Model(input=input_layer, output=output)
        model.compile(rmsprop(lr=self.model_learning_rate, clipvalue=1), "mse")

        return model
    
