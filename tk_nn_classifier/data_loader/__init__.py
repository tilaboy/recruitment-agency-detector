'''module to load data and split data'''
from typing import Dict, Generator, Tuple, List
import os
import sys
from ..exceptions import FileTypeError, ConfigError
from .csv_loader import CSVLoader, split_csv_file
from .trxml_loader import TRXMLLoader, split_trxml_set
from .data_utils import file_ext

def _data_type(data_path: str) -> str:
    data_type = None
    if os.path.isdir(data_path):
        # TODO: check at least on trxml exist
        data_type = 'TRXML'
    elif os.path.isfile(data_path):
        file_extension = file_ext(data_path)
        if file_extension in ['csv', 'tsv']:
            data_type = 'CSV'
        else:
            raise FileTypeError(file_ext)
    else:
        raise FileNotFoundError(f'{data_path} not found')
    return data_type


def _select_data_reader(config_input_feature: Dict, data_type: str):
    loader_class = getattr(sys.modules[__name__], data_type + 'Loader')
    return loader_class(config_input_feature)

def _type_to_config_field_entry(data_type: str) -> str:
    return data_type.lower() + '_fields'


def load_data_set(config: Dict,
                  data_path: str,
                  train_mode: bool=True) ->Generator:
    '''
    load data:

    params:
        - field_config: fields need to load
        - data_path: data file
        - train_mode: load data only used for train, or also doc_id and extra fields

    output:
        - data_set: a list of dic in the form of {field_0: value, field_1: value, ...}
    '''
    data_type = _data_type(data_path)
    field_entry = _type_to_config_field_entry(data_type)
    if field_entry not in config:
        raise ConfigError(
            field_entry,
            section='',
            detail_msg=f'fields {field_entry} not set, failed loading data')

    data_reader = _select_data_reader(config[field_entry], data_type)
    if train_mode:
        return data_reader.load_train_data(data_path)
    else:
        return data_reader.load_detail_data(data_path)


def split_data_set(data_path: str,
                   ratio: float=0.8,
                   des: str='models',
                   rand_seed: int=111) -> Tuple[str, str]:
    '''
    split the data into train and evel

    params:
        - data_path: input data path
        - ratio: a float number x in [0, 1], x will be train,
                 and 1 - x will be eval
        - des: output folder, generate des/train.csv, and des/eval.csv
        - rand_seed: random number seed

    output:
        - train_file_path
        - eval_file_path
    '''
    data_type = _data_type(data_path)
    if data_type == 'TRXML':
        train_set, eval_set = split_trxml_set(data_path, ratio, des, rand_seed)
    elif data_type == 'CSV':
        train_set, eval_set = split_csv_file(data_path, ratio, des, rand_seed)
    return train_set, eval_set
