import sys
import os
sys.path.append('../src')

from read_data import Data
from analysis import analysis
import yaml
from time import sleep
import deeplabcut

def yaml_exists(image_folder):
    '''
        check if yaml exists in this folder.
    '''

    if any(File == "config.yaml" for File in os.listdir("image_folder")):
        print( "You've preiously used this folder to create a model. Would you like to continue using the same analysis? (yes/no)")
        if (input() == "yes"):
            return True
        else:
            print("Deleting previous analysis")
            os.remove(os.path.join(image_folder, "config.yaml"))
            return False
    else:
        return False

if __name__ == '__main__':

    user = os.getenv("USER")
    data_dir = "/gpfs/data/rcretonp/experiment_data"

    # get experiment directory from USER
    print("Which folder would you like to analyze?")
    print("Possible options are :")
    for item in os.listdir(os.path.join(data_dir, user)):
        if os.path.isdir(item):
            print(item)

    experiment_dir = input()

    image_folder = os.path.join(data_dir, user, experiment_dir)
    first_time = not yaml_exists(image_folder)
    config_file = os.path.join(image_folder, "config.yaml")

    if first_time:
        cfg = yaml.load(config_file)
        image_folder = cfg['image_folder']

    print("Loading images ...")

    images = Data(image_folder + '/IMG_%04d.JPG')
    print("Please check if the image is loaded properly. A plot should open up shortly.")
    sleep(5)

    ret, image, _ = images.read(plot = True)
    if not ret:
        print("Images could not be loaded. Possible reasons")
        print("1. Images are directly not under this folder. If so please provide the folder where the images are stored")
        print("2. Images are not named IMG_%04d.JPG -> first image = IMG_0001.JPG, 1400th image = IMG_1400.JPG .")
        print("Closing this session. Please launch again with recommended changes")
        sys.exit()

    images.reset()

    print("Was the image loaded properly? (yes/no)")

    if (input() == "no"):
        print("Images could not be loaded")
        print("Closing this session")
        sys.exit()

    print("Detecting wells ...")

    if first_time:
        rmin, rmax = map(int, input("Input estimated minimum and maximum radius of wells. If you want to continue with defaults type 72 100").split())
    else :
        rmin = cfg['rmin']
        rmax = cfg['rmax']
    
    wells = experiment.detect_wells(R = [rmin, rmax])

    print("Total of {} wells detected. A plot should open up shortly".format(len(wells)))
    sleep(5)
    experiment.plot_wells(wells)

    print("Were the wells detected properly? (yes/no)")
    wells_correct = (input() == "yes")

    while not wells_correct:
        rmin, rmax = input("Please input different values for minimum and maximum estimated radii").split()
        wells = experiment.detect_wells(R = [rmin, rmax])

        print("Total of {} wells detected. A plot should open up shortly".format(len(wells)))
        sleep(5)
        experiment.plot_wells(wells)

        print("Were the wells detected properly? (yes/no)")
        wells_correct = (input() == "yes")

    if first_time:
        cropped_dir = os.path.join(image_folder, "cropped_dir")

        try:
            os.makedirs(cropped_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e

        print("Cropping wells. This might take a while ....")

        filenames = experiment.crop_to_video(wells, cropped_dir=cropped_dir, no_wells_to_record = 6)

        print("Done")
    else :
        cropped_dir = cfg['cropped_dir']
        filenames = cfg['filenames']
        print("There were a total of {} videos in cropped directory.".format(len(filenames)))

    print("Storing progress in config.yaml ...")

    cfg = [{    'image_folder': image_folder,
                'rmin': rmin,
                'rmax': rmax,
                'cropped_dir': cropped_dir,
                'filenames': filenames     }]


    with (open(config_file, "r+") as f):
        f.write(yaml.dumps(cfg))
        f.close()

    print("Done")

    project_dir = os.path.join(image_folder, 'DLC_model_training')

    try:
        os.makedirs(cropped_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    project_name = input("Please input a name for your project. e.g. MyFirstModel/ My_First_Project (Note there shouldn't be any spaces in the name)")
    experimenter = input("Please input who is conducting this analysis")

    DLC_config = deeplabcut.create_new_project(  project_name,
                                    experimenter,
                                    filenames,
                                    working_directory = project_dir,
                                    copy_videos = False)
    
    bodyparts = list(input("What bodyparts would you want to be detected? e.g. right_eye left_eye yolk").split())
    total_number_of_frames = int(input("Total number of frames you would like to label. The higher this number the better the model."))

    cfg['created_project'] = True

    print("Storing progress in config.yaml ...")

    with (open(config_file, "r+") as f):
        f.write(yaml.dumps(cfg))
        f.close()

    print("Done")
    
    deeplabcut.extract_frames(DLC_config, mode = 'automatic', algo = 'kmeans', userfeedback = False)
    cfg['extracted_frames'] = True

    print("Storing progress in config.yaml ...")

    with (open(config_file, "r+") as f):
        f.write(yaml.dumps(cfg))
        f.close()

    print("Done")
    
    deeplabcut.label_frames(DLC_config)
    cfg['labeled_frames'] = True
    print("Storing progress in config.yaml ...")

    with (open(config_file, "r+") as f):
        f.write(yaml.dumps(cfg))
        f.close()

    print("Done")

    deeplabcut.create_training_dataset(DLC_config, augmenter_type = 'imgaug')
    cfg['created_training_dataset'] = True

    print("Storing progress in config.yaml ...")

    with (open(config_file, "r+") as f):
        f.write(yaml.dumps(cfg))
        f.close()

    print("Done")
    
    posefile, _, _ = deeplabcut.return_train_network_path(DLC_config)
    edits = {"save_iters": 15000, "display_iters": 1000}
    _ = deeplabcut.auxiliaryfunctions.edit_config(posefile, edits)

    maxiters = int(input("How many iterations do you want the model to train? The larger this number the accurate the model. should be greater than 15000"))

    while True:
        
        deeplabcut.train_network(DLC_config, max_snapshots_to_keep=3)
        
        print("Evaluating ...")
        deeplabcut.evaluate_network(DLC_config, plotting = True)

        print("Done")

        print("Please check if the model is good enough using evaluation results.")
        to_continue = (input("Is the model good enough? (yes/no)") == "yes")
        if (to_continue)
            print("Cropping another video for analysis ...")
            filenames = experiment.crop_to_video(wells, cropped_dir=cropped_dir, no_wells_to_record = 6)
            deeplabcut.extract_outlier_frames(DLC_config, filenames)
            deeplabcut.refine_labels(DLC_config)
            deeplabcut.merge_datasets(DLC_config)
            deeplabcut.create_training_dataset(DLC_config, augmenter_type = 'imgaug')
        else :
            break

    print("Congratulations!!! You've trained a model")
    sleep(2)

    print("Storing the model ...")
    deeplabcut.export_model(DLC_config)

    cfg = auxiliaryfunctions.read_config(cfg_path)
    project_path = os.path.dirname(os.path.realpath(cfg_path))
    print("Your model is stored in {}".format(project_path + "/" + "exported-models"))

    print("Done")
    print("Closing training session")