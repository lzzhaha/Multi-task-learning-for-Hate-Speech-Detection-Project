"""
Utility methods for data processing.
"""
import os
from glob import glob
import itertools
import csv
import pandas as pd
from constants import NUM, NUMBERREGEX, UNK, WORD_START, WORD_END, EMBEDS_FILES, FULL_LANG, LABELS



def get_label(label2id, id_sequence, file): 
    #Convert label_id seuqence to label sequence and write to file
    label_list = [0]*len(label2id)

    for label, idx in label2id.items():
        label_list[idx] = label

    count = 1
    with open(file, 'w') as f:
        for label_idx_seq in id_sequence:
            label_seq = []

            for idx, label_idx in enumerate(label_idx_seq):
                if(label_idx==1):
                    label_seq.append(label_list[idx])

            f.write(str(count) +'.\t'+','.join(label_seq) +'\n')
            count+=1

        f.close()

def normalize(word):
    """Normalize a word by lower-casing it or replacing it if it is a number."""
    return NUM if NUMBERREGEX.match(word) else word.lower()

def average_by_task(score_dict): 
#Compute unweighted average of all metrics among all tasks
    total = 0
    count = 0

    for key in score_dict:
     
        total+=(score_dict[key]['micro_f1'] + score_dict[key]['macro_f1'])
        count+=2


    return total/float(count)

def average_by_lang(score_list, data_size_list, total_data_size): 
    #Compute weighted average of all languages
    res = 0

    for idx in range(len(score_list)):
        ratio = float(data_size_list[idx]) / total_data_size
        res += ratio * score_list[idx]

    return res

def load_embeddings_file(embeds, languages, sep=" ", lower=False):
    """Loads a word embedding file."""


    embed_dir = EMBEDS_FILES[embeds]
    file_name_list = []
    for f in os.listdir(embed_dir):
        if (any([f.endswith(lang+'.vec') for lang in languages])):
            file_name_list.append(os.path.join(embed_dir,f))


    word2vec = {}
    total_num_words = 0
    embed_dim = 0
    encoding = None
    for file_name in file_name_list:
        print('\n\n Loading {}.....\n\n'.format(file_name))
        if(file_name.endswith('ar.vec') or file_name.endswith('fr.vec')):
            encoding='utf-8'
        with open(file=file_name, mode='r', encoding=encoding) as f:
            (num_words, embed_dim) = (int(x) for x in f.readline().rstrip('\n').split(' '))
            total_num_words+=num_words
            for idx, line in enumerate(f):
                if((idx+1)%(1e+5)==0):
                    print('Loading {}/{} words'.format(idx+1, num_words))
                fields = line.rstrip('\n').split(sep)
                vec = [float(x) for x in fields[1:]]
                word = fields[0]
                if lower:
                    word = word.lower()
                word2vec[word] = vec
    print('Loaded pre-trained embeddings of dimension: {}, size: {}, lower: {}'
          .format(embed_dim, total_num_words, lower))
    return word2vec, embed_dim






def get_data(languages, task_names, word2id=None, task2label2id=None, data_dir=None,
         train=True, verbose=False):
    """
    :param languages: a list of languages from which to obtain the data
    :param task_names: a list of task names
    :param word2id: a mapping of words to their ids
    :param char2id: a mapping of characters to their ids
    :param task2label2id: a mapping of tasks to a label-to-id dictionary
    :param data_dir: the directory containing the data
    :param train: whether data is used for training (default: True)
    :param verbose: whether to print more information re file reading
    :return X: a list of tuples containing a list of word indices and a list of
               a list of character indices;
            Y: a list of dictionaries mapping a task to a list of label indices;
            org_X: the original words; a list of lists of normalized word forms;
            org_Y: a list of dictionaries mapping a task to a list of labels;
            word2id: a word-to-id mapping;
            char2id: a character-to-id mapping;
            task2label2id: a dictionary mapping a task to a label-to-id mapping.
    """
    X = []
    Y = []
    org_X = []
    org_Y = []

    # for training, we initialize all mappings; for testing, we require mappings
    if train:
 
        # create word-to-id, character-to-id, and task-to-label-to-id mappings
        word2id = {}


        # set the indices of the special characters
        word2id[UNK] = 0  # unk word / OOV


    for language in languages:
        num_sentences = 0
        num_tokens = 0

        full_lang = FULL_LANG[language]
        #file_reader = iter(())
        language_path = os.path.join(data_dir, full_lang)


        assert os.path.exists(language_path), ('language path %s does not exist.'
                                             % language_path)

        csv_file = os.path.join(language_path,os.listdir(language_path)[0])

        df = pd.read_csv(csv_file)


        #Column headers are HITId, tweet, sentiment, directness, annotator_sentiment, target, group

        for index, instance in df.iterrows():
            num_sentences+=1
            #sentence = instance['tweet'].split()
            sentence = instance['tweet'].split()

            sentence_word_indices = []  # sequence of word indices
            sentence_char_indices = []  # sequence of char indice

            # keep track of the label indices and labels for each task
            sentence_task2label_indices = {}

            for i, word in enumerate(sentence):
                num_tokens+=1

                if train and word not in word2id:
                    word2id[word] = len(word2id)

                sentence_word_indices.append(word2id.get(word, word2id[UNK]))

        


            labels = None

            for task in task2label2id.keys():
                if('sentiment' in task):
                  labels = instance[task].split('_')
                else:
                  labels = [instance[task]]
                
                if('sentiment' in task):#Multi-label

                    sentence_task2label_indices[task]=[0]*len(task2label2id[task])

                    for label in labels:
                        label_idx = task2label2id[task][label]
                        sentence_task2label_indices[task][label_idx]=1


                else:

                    sentence_task2label_indices[task] = [task2label2id[task][labels[0]]]


            X.append(sentence_word_indices)
            Y.append(sentence_task2label_indices)

    assert len(X) == len(Y)
    return X, Y, word2id
      


#Log the training process

def log_fit(log_dir, epoch, languages, test_lang, task_names, train_score, dev_score):
    

    if(len(task_names) ==1):
        task_name = task_names[0]

        if(len(languages) == 1):

            file = os.path.join(log_dir, 'STSL/{}_{}.csv'.format(languages[0],task_names[0]))

        else:

            file = os.path.join(log_dir, 'STML/{}.csv'.format(task_names[0]))


        if(os.path.exists(file)):
            with open(file, 'a') as f:
                writer = csv.writer(f,delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)


            writer.writerow([epoch, test_lang, train_score[task_name]['micro_f1'], train_score[task_name]['macro_f1'], 
                    dev_score[task_name]['micro_f1'], dev_score[task_name]['macro_f1']])                        
        
        else:
            with open(file, 'a') as f:
                writer = csv.writer(f,delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

                writer.writerow(['epoch',  'test_lang', task_name+'-train-micro-f1',  task_name+'-train-macro-f1', 
                    task_name+'-dev-micro-f1',  task_name+'-dev-macro-f1'])

                writer.writerow([epoch, test_lang, train_score[task_name]['micro_f1'], train_score[task_name]['macro_f1'], 
                    dev_score[task_name]['micro_f1'], dev_score[task_name]['macro_f1']])
                        
                f.close()

    else:

        if(len(languages) ==1):

            file = os.path.join(log_dir, 'MTSL/{}.csv'.format(languages[0]))

        else:
            file = os.path.join(log_dir, 'MTML/log.csv')


        task_name_list = []

        task_f1_list = []
 
        for task in task_names:
            task_name_list+=[task_name+'-train-micro-f1',  task_name+'-train-macro-f1', 
                    task_name+'-dev-micro-f1',  task_name+'-dev-macro-f1']

            task_f1_list +=[train_score[task_name]['micro_f1'], train_score[task_name]['macro_f1'], 
                    dev_score[task_name]['micro_f1'], dev_score[task_name]['macro_f1']]


        if(os.path.exists(file)):
            with open(file, 'a') as f:
                writer = csv.writer(f,delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                writer.writerow([epoch, test_lang]+  task_f1_list)

                f.close()

        else:
            with open(file, 'a') as f:
                writer = csv.writer(f,delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['epoch', 'test_lang'] + task_name_list )
                writer.writerow([epoch, test_lang]+  task_f1_list )


                f.close()
                



#Log the final score
        
def log_score(log_dir, languages, test_lang, task_names, embeds,h_dim, cross_stitch_init,
    constraint_weight, sigma, optimizer, train_score, dev_score, test_score):
    

    if(len(task_names) ==1):
        task_name = task_names[0]

        if(len(languages) == 1):

            file = os.path.join(log_dir, 'STSL/{}_{}.csv'.format(languages[0],task_names[0]))

        else:

            file = os.path.join(log_dir, 'STML/{}.csv'.format(task_names[0]))


        if(os.path.exists(file)):
            with open(file, 'a') as f:
                writer = csv.writer(f,delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)


                writer.writerow([embeds,test_lang, h_dim, cross_stitch_init, constraint_weight, sigma, optimizer,
                        train_score[task_name]['micro_f1'], train_score[task_name]['macro_f1'], 
                        dev_score[task_name]['micro_f1'], dev_score[task_name]['macro_f1'], 
                        test_score[task_name]['micro_f1'], test_score[task_name]['macro_f1']])
                        
        else:
            with open(file, 'a') as f:
                writer = csv.writer(f,delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

                writer.writerow(['embeds', 'test_lang', 'h_dim', 'cross_stitch_init', 'constraint_weight', 'sigma', 'optimizer',
                       task_name+'-train-micro-f1',  task_name+'-train-macro-f1', task_name+'-dev-micro-f1',  task_name+'-dev-macro-f1', 
                       task_name+'-test-micro-f1',  task_name+'-test-macro-f1'])

                writer.writerow([embeds,test_lang, h_dim, cross_stitch_init, constraint_weight, sigma, optimizer,\
                        train_score[task_name]['micro_f1'], train_score[task_name]['macro_f1'], 
                        dev_score[task_name]['micro_f1'], dev_score[task_name]['macro_f1'], 
                        test_score[task_name]['micro_f1'], test_score[task_name]['macro_f1']])

                f.close()

    else:

        if(len(languages) ==1):

            file = os.path.join(log_dir, 'MTSL/{}.csv'.format(languages[0]))

        else:
            file = os.path.join(log_dir, 'MTML/log.csv')


        task_name_list = []

        task_f1_list = []
 
        for task in task_names:
            task_name_list+=[task+'-train-micro-f1', task+'-train-macro-f1', task+'-dev-micro-f1', task+'-dev-macro-f1', task+'-test-micro-f1', task+'-test-macro-f1']

            task_f1_list +=[ train_score[task]['micro_f1'], train_score[task]['macro_f1'], dev_score[task]['micro_f1'], dev_score[task]['macro_f1'], test_score[task]['micro_f1'], test_score[task]['macro_f1']]

        if(os.path.exists(file)):
            with open(file, 'a') as f:
                writer = csv.writer(f,delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                writer.writerow([embeds, test_lang, h_dim, cross_stitch_init, constraint_weight, sigma,optimizer]+\
                    task_f1_list)

                f.close()

        else:
            with open(file, 'a') as f:
                writer = csv.writer(f,delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['embeds', 'test_lang', 'h_dim', 'cross_stitch_init', 'constraint_weight', 'sigma']\
                    +task_name_list)
                writer.writerow([embeds, test_lang,h_dim, cross_stitch_init, constraint_weight, sigma,optimizer]+\
                    task_f1_list )

                f.close()
                



