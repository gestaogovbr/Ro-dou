import os


def get_source_dir() -> str:
    base_dir = os.path.join(os.environ['AIRFLOW_HOME'], 'dags')
    dir_name = 'ro_dou'

    # Walk through the directory tree to find the directory
    for root, dirs, files in os.walk(base_dir):
        if dir_name in dirs:
            # If the directory is found, print its path and exit the loop
            return os.path.join(root, dir_name)
    else:
        # If the directory is not found, print a message
        raise Exception(f"{dir_name} directory not found "
                        f"in {base_dir} or its subdirectories.")

