import json

TURN_TEMPLATE = '<p class="{party}" title="Auto Accident"> {turn} </p>'
SUMMARY_TEMPLATE = '<short_summary>\n{summary}\n</short_summary>'
INSTRUCTION_TEMPLATE = 'Have the following instruction be applied in the p.innerHTML.\ninstruction: {instruction}\n'
DIV_PREFIX_INSTRUCTION = 'Have [AGENT] asks a question for car accident details.'
CANDIDATE_NOT_FOUND_PROMPT = ''
CANDIDATE_TOO_MANY_PROMPT = ''

CHATGPT_REWRITE_TURNS_SCENARIO = "You are a conversation rewriter."
CHATGPT_REWRITE_QUERY_RESULT_SCENARIO = "Paraphrase the following list of tuples into natural language"
CHATGPT_REWRITE_SCENARIO = "You are a translator to translate from written text to conversational language. Make sure you keep most of the content."
CHATGPT_REWRITE_SCENARIO = "Make sure you keep most of the content."
CHATGPT_SUBDIALOG_SCENARIO = (
    "You are a dialogue copilot to complete the conversation. "
    "Generate the next <div> block with less than 10 <p>. "
    "The content in the <div> block should be coherent to the previous dialogues."
)
CHATGPT_STORY_GENERATION_SCENARIO = "You are a story generator to create a detailed car accident story."

AGENT_TURN_REWRITE_TEMPLATE = "Paraphrase the sentence from the agent in a car accident claim call to sound more conversational."
USER_TURN_REWRITE_TEMPLATE = "Paraphrase the sentence from the caller in a car accident claim call to sound more conversational."
TURN_REWRITE_TURNS_TEMPLATE = "Each pair of <p> </p> tags mean a turn. Make sure the speakers alternate each other between <p> </p> tags."

CANDIDATE_NOT_FOUND_TEMPLATE = 'No options found for {domain}. [AGENT] should ask [USER] to relax search condition.'
CANDIDATE_TEMPLATE = '[AGENT] should only provide the {domain} appearing in the tuples in the candidate list. Here is the list of candidates for {domain}:'

PROMPT_DIR = './data/prompts'
FLOW_DIR = './data/flows'
API_KEY_PATH = './.api_keys'
WORKER_MAP_PATH = './data/worker_table.yaml'
TASK_TABLE_PATH = './data/task_table.yaml'
DATABASE_CONFIG_PATH = './data/database_config.yml'

FINISHED = '[FNISHED]'
TASK_DIR_TEMPLATE = './data/tasks/{}'
ITER_DIR_TEMPLATE = './data/tasks/{}/iteration_{:03}'
SUCCESS_FILENAME = 'success.yaml'
RELABELING_FILENAME = 'relabeling.yaml'
RELABELING_IAA_FILENAME = 'relabeling_iaa.yaml'
FINAL_REVIEW_FILENAME = 'final_review.yaml'
TURN_SEP = '\n'

DEFAULT_INSTRUCTIONS = [
    "Have {user_name} misremember the details. {agent_name} double check with {user_name}.",
    "Have {user_name}'s response be less specific. Have {agent_name} asks for more details.",
    "Have {user_name} correct wrong information. Have {agent_name} asks for clarification.",
    "Have {user_name} describe more car accident details with complex reasoning that involves two cars' motion.",
    "Have {agent_name} ask [MISSING SLOT VALUE].",
    "Have {user_name} mention [MISSING SLOT VALUE].",
]

# Do this for each task instead of using global var.
with open('./data/schema/ontology.json', 'r') as f:
    SCHEMA = json.load(f)

DOMAINS = sorted([domain['val'] for domain in SCHEMA['schema']])

API_KEYS = []
with open(API_KEY_PATH, 'r') as f:
    for line in f:
        if line.startswith('#'):
            continue
        API_KEYS.append(line.strip())
