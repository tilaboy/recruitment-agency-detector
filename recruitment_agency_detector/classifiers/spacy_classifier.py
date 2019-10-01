import os
import spacy
import json
from pathlib import Path
import random
from spacy.util import minibatch, compounding

from ..data_loader import SpacyDataReader
from .. import LOGGER
from .utils import TrainHelper

class SpaceClassifier:
    def __init__(self, config):
        self.config = config
        self.type = config['model_type']
        self.data_reader = SpacyDataReader(self.config)

    def build_and_train(self):
        self.build_graph()

        train_data=self.data_reader.get_data(
            self.config['datasets']['train'],
            shuffle=True,
            train_mode=True
        )
        eval_data=self.data_reader.get_data(self.config['datasets']['eval'])
        textcat = self.train(train_data, eval_data)
        if 'test' in self.config['datasets']:
            self.evaluate_on_tests(textcat)

    def build_graph(self):
        if self.config["spacy"]["model"] is not None:
            model = spacy.load(self.config["spacy"]["model"])
            LOGGER.info("Loaded model '%s'" % self.config["spacy"]["model"])
        else:
            model = spacy.blank(self.config["spacy"]["language"])  # create blank Language class
            LOGGER.info("Created blank '%s' model" % self.config["spacy"]["language"])

        # add the text classifier to the pipeline if it doesn't exist
        # nlp.create_pipe works for built-ins that are registered with spaCy
        if "textcat" not in model.pipe_names:
            textcat = model.create_pipe(
                "textcat",
                config={
                    "exclusive_classes": True,
                    "architecture": self.config["spacy"]["arch"],
                }
            )
            model.add_pipe(textcat, last=True)
        self.model =  model

    def train(self, train_data, eval_data):
        textcat = self.model.get_pipe("textcat")
        for label in self.data_reader.label_mapper.label_to_classid:
            textcat.add_label(label)

        # get names of other pipes to disable them during training
        other_pipes = [pipe for pipe in self.model.pipe_names if pipe != "textcat"]

        with self.model.disable_pipes(*other_pipes):  # only train textcat
            self.optimizer = self.model.begin_training()
            if self.config.get('init_tok2vec', None) is not None:
                init_tok2vec = Path(self.config['init_tok2vec'])
                with init_tok2vec.open("rb") as file_:
                    textcat.model.tok2vec.from_bytes(file_.read())
            LOGGER.info("Training the model...")
            TrainHelper.print_progress_header()
            batch_sizes = compounding(4.0, 32.0, 1.001)

            for i in range(self.config['num_epochs']):
                losses = self._update_one_epoch(train_data, batch_sizes)
                scores = self.evaluate(eval_data, textcat)
                TrainHelper.print_progress(losses["textcat"], scores)

        return textcat

    def _update_one_epoch(self, train_data, batch_sizes):
        losses = {}
        # batch up the examples using spaCy's minibatch
        random.shuffle(train_data)
        batches = minibatch(train_data, size=batch_sizes)
        for batch in batches:
            texts, annotations = zip(*batch)
            self.model.update(
                              texts,
                              annotations,
                              sgd=self.optimizer,
                              drop=self.config["dropout_rate"],
                              losses=losses
                              )
        return losses

    def load_saved_model(self, model_path=None):
        if model_path is None:
            model_path = self.config['model_path']
        self.model = spacy.load(model_path)

    def save(self, output_dir):
        if output_dir is not None:
            output_dir = Path(output_dir)
            if not output_dir.exists():
                output_dir.mkdir()
            with self.model.use_params(self.optimizer.averages):
                self.model.to_disk(output_dir)
            print("Saved model to", output_dir)

    def process_with_saved_model(self, input):
        result = self.model(input)
        doc = self.model(test_text)
        return [ doc.cats[label] for lable in uniq_lables ]

    def evaluate_on_tests(self, textcat):
        for test_set in self.config['datasets']['test']:
            test_data = self.data_reader.get_data(
                    self.config['datasets']['test'][test_set])
            texts, cats = zip(*test_data)
            predicted_classes = list(self.predict_batch(texts))
            TrainHelper.eval_and_print(test_set, predicted_classes, lables)

    def evaluate(self, eval_data, textcat):
        texts, cats = zip(*eval_data)
        predicted_cats = list(self.predict_batch(texts))
        with textcat.model.use_params(self.optimizer.averages):
            score = TrainHelper._evaluate_score(predicted_cats, cats)
        return score

    def predict_batch(self, texts):
        textcat = self.model.get_pipe("textcat")
        docs = (self.model.tokenizer(text) for text in texts)
        for doc in textcat.pipe(docs):
            yield doc.cats
