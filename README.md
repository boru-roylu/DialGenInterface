# DialGenInterface
<img src="img/uwnlp_logo.png" width="10%" align="right"> 


The offical implementation of dialog generation (<span style="font-variant:small-caps;">DialGen</span>) framework with ChatGPT. Please refer to our paper for details.

**DIALGEN: Collaborative Human-LM Generated Dialogues for Improved Understanding of Human-Human Conversations**.

[Bo-Ru Lu](https://nlp.borulu.com/)<sup>1*</sup>, Nikita Haduong<sup>1*</sup>, [Chia-Hsuan Lee](https://chiahsuan156.github.io/)<sup>1</sup>, [Zeqiu Wu](http://ellenmellon.github.io/)<sup>1</sup>, [Hao Cheng](https://sites.google.com/site/hcheng2site/Home)<sup>2</sup>, Paul Koester<sup>3</sup>, Jean Utke<sup>3</sup>, [Tao Yu](https://taoyds.github.io)<sup>4</sup>, [Noah A. Smith](https://nasmith.github.io/)<sup>1,5</sup> and [Mari Ostendorf](https://people.ece.uw.edu/ostendorf/)<sup>1</sup>. <sup>\*</sup>Equal Contribution</span>

<sup>1</sup>University of Washington</span> <sup>2</sup>Microsoft Research</span> <sup>3</sup>Allstate</span> <sup>4</sup>University of Hong Kong</span> <sup>5</sup>Allen Institute for AI</span>

[[project]](https://nlp.borulu.com/DialGen/) [[data]](https://github.com/boru-roylu/DialGenModel/tree/main/dialgen_data/v1.0) [[model]](https://github.com/boru-roylu/DialGenModel/tree/main) [[paper]](https://arxiv.org/abs/2307.07047) [[interface]](https://github.com/boru-roylu/DialGenInterface)


If you use our source codes included in this repository in your work, please cite the our paper. The bibtex is listed below:

```
@misc{lu2023dialgen,
      title={DIALGEN: Collaborative Human-LM Generated Dialogues for Improved Understanding of Human-Human Conversations}, 
      author={Bo-Ru Lu and Nikita Haduong and Chia-Hsuan Lee and Zeqiu Wu and Hao Cheng and Paul Koester and Jean Utke and Tao Yu and Noah A. Smith and Mari Ostendorf},
      year={2023},
      eprint={2307.07047},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
```

## Local Website Setup 

### Step1: Setup for OpenAI API Keys
Put your OpenAI API keys in the file `.api_keys`. Multiple keys are allowed. Put them line by line.
More keys will ensure a shorter lentency for multiple concurrent tasks at the same time.

### Step 2 (optional): Task Preparation
Since We have prepared 5 initial tasks, please check the directory `data/flows/[Accident Location]/[task ID]` for the details of each task.
The 5 tasks are generated via `create_tasks.ipynb`. If you would like to create more tasks, you need to prepare the tasks first.

To generate data with your own domain, you can update the `data/schema/ontology.csv` and run `convert_schema_from_csv_to_json.ipynb`. After that, use `create_tasks.ipynb` to create your own tasks. You may also change your template prompts in `data/prompts` and `src/config.py`.

### Step 3: Build and run containers

```bash
docker-compose up --build
```

You can read `create_tasks.ipynb` for reference. If you want to generate your own data, you should provide `data/schema/ontology.csv` yourself.

### Step 4: Task Initialization
After containers are running, use the following link to initialize the prepared tasks for data generation.
It may take some time to initialize all the tasks provided in the `data/task_table.yaml`. Each task take around 1 minute.

http://localhost:5001/admin

### Step 5: Start to generate data and annotate them!

Links to the prebuilt tasks. The link format is http://localhost:5001/main?task_id=[task_id]&worker_id=[worker_id]

- task_id = '8MGFw'; worker_id = bobsmith \
  link = http://localhost:5001/main?task_id=8MGFw&worker_id=bobsmith
- task_id = 'JT3cM'; worker_id = bobsmith \
  link = http://localhost:5001/main?task_id=JT3cM&worker_id=bobsmith
- task_id = 'sTXKs'; worker_id = bobsmith \
  link = http://localhost:5001/main?task_id=sTXKs&worker_id=bobsmith
- task_id = '903w4'; worker_id = bobsmith \
  link = http://localhost:5001/main?task_id=903w4&worker_id=bobsmith
- task_id = 'a1DA3'; worker_id = bobsmith \
  link = http://localhost:5001/main?task_id=a1DA3&worker_id=bobsmith


## Website Interface
Our DialGen framework is designed to generate schema-guided dialogues through human-LM collaboration. An LM is selected as the backbone, then the data generation process begins with an initial task prompt consisting of natural language description for the desired dialogue (e.g., task description, desired slots, story and personalities) and dialogue history. During each iteration, the LM first proposes a candidate subdialogue based on the history (the initial task prompt and the generated conversation so far). Human reviewers with sufficient domain knowledge then validate, edit, and annotate the generated subdialogue, before requesting a continuation via an updated prompt to the LM. The reviewers can optionally augment the prompt with a specific instruction related to the desired dialogue flow. This process repeats until the dialogue is complete. At a high level, the human-in-the-loop mechanism ensures that the resulting dialogues are coherent and consistent with the prompt, covering desired content and fulfilling style specifications from domain experts.
<img src="img/dg_fig_pipeline.jpeg" alt="pipeline" width="1000"/>

### Training Documents
We offer our human reviewers the [training documentation](https://docs.google.com/document/d/1OGXufpHPivT9zHzo9PU4gD6OhT--PGajVx--gARnaNc/edit?usp=sharing) as a guideline, providing comprehensive instructions on how to navigate and utilize this website interface.


### Subdialog Generation & Revise
The subdialog generation process iteratively proceeds until the human reviewer decide the entire dialog finishes.
<img src="img/editing.png" alt="editing step" width="700"/>

### Subdialog Annotation (Label)
The labeling step follows each subdialog generation step for easier labeling purpose because the same human review will just review the generated subdialog and can label the subdialog more efficiently. This step can be entirely decoupled from the framework.
<img src="img/labeling.png" alt="labeling step" width="700"/>

### Final Review for the Entire Dialog
This step is for human reviewers to finally check if there is any mislabeling or disfluent turns.
<img src="img/final_review.png" alt="final review step" width="700"/>

### Download the Generated files
This step involves saving data. We offer raw files in both yaml (comprehensive details) and xlsx (user-friendly) formats. We adhere to the MultiWoZ data format for storing our preprocessed data. These formats serve different purposes for three distinct modeling methods. First, in turn-level belief (TLB) modeling, the models need to forecast the TLB for each user and agent turn. Second, in dialog state tracking (DST) modeling, the models must predict all slots and values up to turn $t$. Lastly, in state change modeling, the model must predict the updated slots and values along with the corresponding operations between dialog states from the previous user-agent turn to the current user-agent turn.
<img src="img/download.png" alt="download" width="700"/>