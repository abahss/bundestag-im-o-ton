import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import pandas as pd
import nltk.data
from practicepreach.rag import Rag
from practicepreach.constants import BUNDESTAG_WAHLPERIODE

model = AutoModelForSequenceClassification.from_pretrained("manifesto-project/manifestoberta-xlm-roberta-56policy-topics-context-2023-1-1", trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained("xlm-roberta-large")

def preprocessing(speech:list, window_start:int, window_stop:int, target_sentence:int):

    context = speech[window_start:window_stop]
    sentence = speech[target_sentence]

    inputs = tokenizer(sentence,
                   " ".join(context),
                   return_tensors="pt",
                   max_length=300,  #we limited the input to 300 tokens during finetuning
                   padding="max_length",
                   truncation=True
                   )
    return inputs

def predict(inputs):
    logits = model(**inputs).logits

    probabilities = torch.softmax(logits, dim=1).tolist()[0]
    probabilities = {model.config.id2label[index]: round(probability * 100, 2) for index, probability in enumerate(probabilities)}
    probabilities = dict(sorted(probabilities.items(), key=lambda item: item[1], reverse=True))

    return probabilities

rag = Rag()
start_date = BUNDESTAG_WAHLPERIODE.get(20)[0]
end_date = BUNDESTAG_WAHLPERIODE.get(20)[1]
chunks = rag.retrieve_topic_chunks('Was sagt die Partei über Migration?','SPD',start_date,end_date,'speech')
speech_content = "\n\n".join(doc.page_content for doc, _ in chunks)

tokenizer_nltk = nltk.data.load('tokenizers/punkt/german.pickle')
speech = tokenizer_nltk.tokenize(speech_content)

# example data
context_window = 5
max = len(speech)
start = 0

while start <= max:
    end = min(start + context_window, max)
    for i in range(start, end + 1):
        print(f'target sentence: {speech[i]}')
        print(list(predict(preprocessing(speech, start, end, i)))[0])
    start = end + 1
