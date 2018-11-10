# TODO Handle when player hits a tree

import os

import numpy as np

from datetime import datetime
from collections import deque

from .helpers.better_dqn import BDQN

from serpent.game_agent import GameAgent
from serpent.input_controller import KeyboardKey

import serpent.ocr
import serpent.cv

import serpent.utilities

from serpent.sprite_locator import SpriteLocator
from serpent.sprite_identifier import SpriteIdentifier
from serpent.sprite import Sprite

from serpent.frame_grabber import FrameGrabber

#from serpent.machine_learning.reinforcement_learning.ddqn import DDQN
from serpent.machine_learning.reinforcement_learning.keyboard_mouse_action_space import KeyboardMouseActionSpace


class SerpentMarioKartGameAgent(GameAgent):
    RESET   = KeyboardKey.KEY_F7
    #ITEM    = KeyboardKey.KEY_Z
    
    

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.frame_handlers["PLAY"] = self.handle_play
        self.frame_handler_setups["PLAY"] = self.setup_play
        self.analytics_client = None
        self.game_state = None
        self.sprite_locator = SpriteLocator()
        self.previous_location = -2
        self.previous_rewards = deque([])
        
    def setup_play(self):
        
        input_mapping = {
            #"RESET": [KeyboardKey.KEY_F7], 
            "GAS": [KeyboardKey.KEY_A], # A
            #"BRAKE": [KeyboardKey.KEY_LEFT_CTRL], # B
            #"DRIFT": [KeyboardKey.KEY_C], # Right-Trigger
            #"LEFT": [KeyboardKey.KEY_LEFT ], # Analog-Left
            #"RIGHT": [KeyboardKey.KEY_RIGHT], # Analog-Right
            "GASLEFT": [KeyboardKey.KEY_A, KeyboardKey.KEY_LEFT],
            "GASRIGHT": [KeyboardKey.KEY_A, KeyboardKey.KEY_RIGHT],
            #"BRAKELEFT": [KeyboardKey.KEY_LEFT_CTRL, KeyboardKey.KEY_LEFT],
            #"BRAKERIGHT": [KeyboardKey.KEY_LEFT_CTRL, KeyboardKey.KEY_RIGHT],
            #"LEFTDRIFT": [KeyboardKey.KEY_LEFT, KeyboardKey.KEY_C],
            #"RIGHTDRIFT": [KeyboardKey.KEY_RIGHT, KeyboardKey.KEY_C],
            #"GASLEFTDRIFT": [KeyboardKey.KEY_A, KeyboardKey.KEY_LEFT, KeyboardKey.KEY_C],
            #"GASRIGHTDRIFT": [KeyboardKey.KEY_A, KeyboardKey.KEY_RIGHT, KeyboardKey.KEY_C],
            #"BRAKELEFTDRIFT": [KeyboardKey.KEY_LEFT_CTRL, KeyboardKey.KEY_LEFT, KeyboardKey.KEY_C],
            #"BRAKERIGHTDRIFT": [KeyboardKey.KEY_LEFT_CTRL, KeyboardKey.KEY_RIGHT, KeyboardKey.KEY_C]
        }
        
        action_space = KeyboardMouseActionSpace(
            #button_keys = [None, "GAS", "BRAKE", "LEFT", "RIGHT", "GASLEFT", "GASRIGHT", "BRAKELEFT", "BRAKERIGHT",
            #                    "LEFTDRIFT", "RIGHTDRIFT",  "GASLEFTDRIFT", "GASRIGHTDRIFT", "BRAKELEFTDRIFT",
            #                    "BRAKERIGHTDRIFT"]
            button_keys = ["GAS", "GASLEFT", "GASRIGHT"]
        )
        
        model_file_path = "datasets/mario_kart.h5".format("/", os.sep)
        
        self.dqn = BDQN(
            model_file_path = model_file_path,
            input_shape = (100, 100, 4),
            input_mapping = input_mapping,
            action_space = action_space,
            replay_memory_size = 5000,
            max_steps = 10000,
            observe_steps = 0,
            batch_size = 32,
            initial_epsilon = 1,
            final_epsilon = 0.01,
            override_epsilon = False
        )
        
        self.dqn.enter_train_mode()
        
        self.reset_game_state()
        
        # Exit the pause menu when loaded
        self.input_controller.tap_key(KeyboardKey.KEY_F5)

    def handle_play(self, game_frame):
        
        for i, game_frame in enumerate(self.game_frame_buffer.frames):
            self.visual_debugger.store_image_data(
                game_frame.frame,
                game_frame.frame.shape,
                str(i)
            )
    
        if self.dqn.frame_stack is None:
            pipeline_game_frame = FrameGrabber.get_frames(
                [0],
                frame_shape=(100, 100),
                frame_type="PIPELINE",
                dtype="float64"
            ).frames[0]
            
            self.dqn.build_frame_stack(pipeline_game_frame.frame)
            
        else:
            game_frame_buffer = FrameGrabber.get_frames(
                [0, 4, 8, 12],
                frame_shape=(100, 100),
                frame_type="PIPELINE",
                dtype="float64"
            )
            
            Distance_image = serpent.cv.extract_region_from_image(
                game_frame.frame,
                self.game.screen_regions["DISTANCE_ONES"]
            )
            
            query_sprite = Sprite("QUERY", image_data=Distance_image[...,np.newaxis])
            sprite_name = self.sprite_identifier.identify(query_sprite, mode="CONSTELLATION_OF_PIXELS")
            
            #distance = serpent.ocr.perform_ocr(Distance_image)
            distance = 0
            
            reward = self.calculate_reward(distance)
            
            completed_lap = self.completed_lap(distance)
            is_stuck = self.is_stuck(reward)
            
            if self.dqn.mode == "TRAIN":
                
                self.game_state["run_reward"] += reward 
                
                self.dqn.append_to_replay_memory(
                    game_frame_buffer,
                    reward,
                    terminal= is_stuck or completed_lap 
                )
                
                # Every 2000 steps, save latest weights to disk
                if self.dqn.current_step % 200 == 0:
                    self.dqn.save_model_weights(
                        file_path_prefix= "datasets/dqn/"
                    )

                # Every 20000 steps, save weights checkpoint to disk
                if self.dqn.current_step % 2000 == 0:
                    self.dqn.save_model_weights(
                        file_path_prefix= "datasets/dqn/",
                        is_checkpoint=True
                    )
                
            elif self.dqn.mode == "RUN":
                self.dqn.update_frame_stack(game_frame_buffer)
        
            run_time = datetime.now() - self.started_at

            #serpent.utilities.clear_terminal()

            print("SESSION RUN TIME: {} days, {} hours, {} minutes, {} seconds".format(run_time.days, run_time.seconds // 3600, (run_time.seconds // 60) % 60, run_time.seconds % 60))
            print("")
            print("OCR STRING: {}".format(sprite_name))

            print("NEURAL NETWORK:\n")
            self.dqn.output_step_data()
            print("")
            print("CURRENT RUN: {}".format(self.game_state["current_run"]))
            print("CURRENT REWARD: {}".format(reward))
            print("PREVIOUS REWARDS: {}".format(self.previous_rewards))
            print("PREVIOUS SPRITE LOCATION: {}".format(self.previous_location))
            print("CURRENT RUN REWARD: {}".format(self.game_state["run_reward"]))
            print("CURRENT RUN PREDICTED ACTIONS: {}".format(self.game_state["run_predicted_actions"]))
            print("")
            print("LAST RUN DURATION: {} seconds".format(self.game_state["last_run_duration"]))
            print("LAST RUN DISTANCE: {} reward".format(self.game_state["last_run_distance"]))
            print("")
            print("RECORD DISTANCE: {} seconds, {} run, {} reward".format(self.game_state["record_distance"].get('seconds'), self.game_state["record_distance"].get('run'), self.game_state["record_distance"].get('reward')))
            print("RECORD LAP TIME: {} seconds, {} run, {} reward".format(self.game_state["record_lap"].get('seconds'), self.game_state["record_lap"].get('run'), self.game_state["record_lap"].get('reward')))
            print("")
            print("SPRITE NOT FOUND: {} times".format(self.game_state["sprite_not_found"]))
            
            if (completed_lap or is_stuck):
                
                timestamp = datetime.utcnow()
                
                timestamp_delta = timestamp - self.game_state["run_timestamp"]
                self.game_state["last_run_duration"] = timestamp_delta.seconds
                self.game_state["last_run_distance"] = self.game_state["run_reward"]
                
                if(self.game_state["last_run_distance"] > self.game_state["record_distance"].get("reward", 0)):
                    self.game_state["record_distance"] = {
                        "seconds": self.game_state["last_run_duration"],
                        "run": self.game_state["current_run"],
                        "reward": self.game_state["last_run_distance"]
                    }
                
                if(completed_lap and self.game_state["last_run_duration"] < self.game_state["record_lap"].get("seconds", 100000)):
                    self.game_state["record_lap"] = {
                        "seconds": self.game_state["last_run_duration"],
                        "run": self.game_state["current_run"],
                        "reward": self.game_state["last_run_distance"]      
                    }
                
                #np.savetxt("datasets/records/RunData.csv", self.game_state, delimiter = ",")
                
                self.game_state["current_run_steps"] = 0
                
                self.input_controller.handle_keys([])
                
                if self.dqn.mode == "TRAIN":
                    for i in range(0,15):
                        #serpent.utilities.clear_terminal()
                        print(f"TRAINING ON MINI-BATCHES: {i + 1}/16")

                        self.dqn.train_on_mini_batch()
                
                print("Current Epsilon: {}".format(self.dqn.epsilon_greedy_q_policy.epsilon))
                
                self.game_state["run_timestamp"] = datetime.utcnow()
                self.game_state["current_run"] += 1
                self.game_state["run_reward"] = 0
                self.game_state["run_predicted_actions"] = 0
                self.game_state["sprite_not_found"] = 0
                
                self.reset_game()
                
                return None
        
        self.dqn.pick_action()
        self.dqn.generate_action()
        
        chosen_keys = self.dqn.get_input_values()
        
        print(chosen_keys)
        
        if self.dqn.current_action_type == "PREDICTED":
            self.game_state["run_predicted_actions"] += 1
        
        self.input_controller.handle_keys(chosen_keys)
                
        self.dqn.erode_epsilon(factor=2)
        
        self.dqn.next_step()
        
        self.game_state["current_run_steps"] += 1
        
        return
    
    def reset_game_state(self):
        self.game_state = {
            "current_run": 1,
            "current_run_steps": 0,
            "run_reward": 0,
            "run_predicted_actions": 0,
            "run_timestamp": datetime.utcnow(),
            "last_run_duration": 0,
            "last_run_distance": 0,
            "record_distance": dict(),
            "record_lap": dict(),
            "sprite_not_found": 0,
            "previous_frame_bad": False
        }
    
    def reset_game(self):
        
        self.previous_location = -2
        self.previous_rewards = deque([])
        
        self.input_controller.tap_key(KeyboardKey.KEY_F5)
    
    def is_stuck(self, reward):
        
        if(len(self.previous_rewards) >= 10):
            curr_sum = 0
            count = 1
            for value in self.previous_rewards:
                curr_sum = curr_sum + value
                count = count + 1
            avr = curr_sum / len(self.previous_rewards)
            self.previous_rewards.popleft()
            self.previous_rewards.append(reward)
            return avr < 1
        else:
            self.previous_rewards.append(reward)
            return False
    
    def completed_lap(self, distance):

        return False
        return distance >= 635
        
    def calculate_reward(self, distance):
        
        return 0
        
        if distance == None:
            self.game_state["sprite_not_found"] += 1
            return 0
        
        reward = distance - self.previous_location
        self.previous_location = distance
        
        return 0
            
        