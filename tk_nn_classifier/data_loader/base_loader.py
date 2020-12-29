'''
Basic class to read files also get the field names relevant to the training
'''
from typing import List, Generator
from ..exceptions import ConfigError

class BaseLoader:
    '''
    Shared functions or properties for data loaders:
        - field names for train, and field names for detailed analysis
        - train_process:
    '''
    def __init__(self, field_config: List):
        self._field_validation(field_config)
        self.field_config = field_config

    @classmethod
    def _field_validation(cls, field_config):
        if 'features' not in field_config:
            raise ConfigError('features', 'csv/trxml_fields')
        if 'class' not in field_config:
            raise ConfigError('class', 'csv/trxml_fields')

    def _load_selected_data(self, fields: List, data_path: str) -> None:
        raise NotImplementedError('_load_selected_data needs to be implemented')

    def _train_fields(self):
        return list(self.field_config['features'].keys()) + [self.field_config['class']]

    def _detail_fields(self):
        fields = self._train_fields()
        if 'doc_id' in self.field_config:
            fields.append(self.field_config['doc_id'])
        if 'extra' in self.field_config:
            fields.extend(self.field_config['extra'])
        return fields

    def load_train_data(self, data_path:str) -> Generator:
        '''load data for training: features, and category'''
        fields = self._train_fields()
        return self._load_selected_data(fields, data_path)

    def load_detail_data(self, data_path:str) -> Generator:
        '''load data for eval and analysis: docid, features and category, and extra'''
        fields = self._detail_fields()
        return self._load_selected_data(fields, data_path)
