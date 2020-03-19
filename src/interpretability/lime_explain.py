from lime.lime_image import *
import pandas as pd
import yaml
import os
import datetime
import dill
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import ImageDataGenerator
#from src.visualization.visualize import visualize_explanation

def predict_instance(x, model):
    '''
    Helper function for LIME explainer. Runs model prediction on perturbations of the example.
    :param x: List of perturbed examples from an example
    :param model: Keras model
    :return: A numpy array comprising a list of class probabilities for each predicted perturbation
    '''
    y = model.predict(x)  # Run prediction on the perturbations
    probs = np.concatenate([1.0 - y, y], axis=1)  # Compute class probabilities from the output of the model
    return probs


def predict_and_explain(x, model, exp, num_features, num_samples):
    '''
    Use the model to predict a single example and apply LIME to generate an explanation.
    :param x: Preprocessed image to predict
    :param model: The trained neural network model
    :param exp: A LimeImageExplainer object
    :param num_features: # of features to use in explanation
    :param num_samples: # of times to perturb the example to be explained
    :return: The LIME explainer for the instance
    '''

    def predict(x):
        '''
        Helper function for LIME explainer. Runs model prediction on perturbations of the example.
        :param x: List of perturbed examples from an example
        :return: A numpy array constituting a list of class probabilities for each predicted perturbation
        '''
        probs = predict_instance(x, model)
        return probs

    # Generate explanation for the example
    explanation = exp.explain_instance(x, predict, num_features=num_features, num_samples=num_samples)
    return explanation


def setup_lime():
    '''
    Load relevant information and create a LIME Explainer
    :return: dict containing important information and objects for explanation experiments
    '''

    # Load relevant constants from project config file
    cfg = yaml.full_load(open(os.getcwd() + "/config.yml", 'r'))
    lime_dict = {}
    lime_dict['NUM_SAMPLES'] = cfg['LIME']['NUM_SAMPLES']
    lime_dict['NUM_FEATURES'] = cfg['LIME']['NUM_FEATURES']
    lime_dict['IMG_PATH'] = cfg['PATHS']['IMAGES']
    lime_dict['TEST_IMGS_PATH'] = cfg['PATHS']['TEST_IMGS']
    lime_dict['PRED_THRESHOLD'] = cfg['PREDICTION']['THRESHOLD']
    KERNEL_WIDTH = cfg['LIME']['KERNEL_WIDTH']
    FEATURE_SELECTION = cfg['LIME']['FEATURE_SELECTION']

    # Load train and test sets
    lime_dict['TRAIN_SET'] = pd.read_csv(cfg['PATHS']['TRAIN_SET'])
    lime_dict['TEST_SET'] = pd.read_csv(cfg['PATHS']['TEST_SET'])

    # Create ImageDataGenerator for test set
    test_img_gen = ImageDataGenerator(rescale=1.0/255.0)
    test_generator = test_img_gen.flow_from_dataframe(dataframe=lime_dict['TEST_SET'], directory=cfg['PATHS']['TEST_IMGS'],
        x_col="filename", y_col="label", target_size=tuple(cfg['DATA']['IMG_DIM']), batch_size=1,
        class_mode='raw', shuffle=False)
    lime_dict['TEST_GENERATOR'] = test_generator

    # Define the LIME explainer
    lime_dict['EXPLAINER'] = LimeImageExplainer(kernel_width=KERNEL_WIDTH, feature_selection=FEATURE_SELECTION,
                                                verbose=True)
    dill.dump(lime_dict['EXPLAINER'], open(cfg['PATHS']['LIME_EXPLAINER'], 'wb'))    # Serialize the explainer

    # Load trained model's weights
    lime_dict['MODEL'] = load_model(cfg['PATHS']['MODEL_TO_LOAD'], compile=False)
    return lime_dict


def explain_xray(lime_dict, idx):
    '''
    # Make a prediction and explain the rationale
    :param lime_dict: dict containing important information and objects for explanation experiments
    :param idx: index of image in test set to explain
    '''

    # Get i'th image in test set
    for i in range(idx + 1):
        x, y = lime_dict['TEST_GENERATOR'].next()
    x = np.squeeze(x, axis=0)

    start_time = datetime.datetime.now()
    explanation = predict_and_explain(x, lime_dict['MODEL'], lime_dict['EXPLAINER'],
                                      lime_dict['NUM_FEATURES'], lime_dict['NUM_SAMPLES'])
    print("Explanation time = " + str((datetime.datetime.now() - start_time).total_seconds()) + " seconds")
    #fig = visualize_explanation(explanation, client_id, lime_dict['Y_TEST'].loc[client_id, 'GroundTruth'],
    #                      file_path=lime_dict['IMG_PATH'])
    return


if __name__ == '__main__':
    lime_dict = setup_lime()
    i = 0                                       # Select i'th image in test set
    explain_xray(lime_dict, i)                  # Generate explanation for image