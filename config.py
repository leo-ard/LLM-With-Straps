import sys
import requests
import ast

def extract_functions_with_doc(filename = 'config.py'):
    """Extracts functions and their docstrings from given a Python file, formatted for language model parsing.

    Args:
        filename (str): path to the Python file

    Returns:
        str: A structured string containing function names and docstrings from all files, formatted for language model parsing.
    """
    output = ""

    with open(filename, 'r') as file:
        node = ast.parse(file.read())

    functions = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]

    for function in functions:
        docstring = ast.get_docstring(function) or "No documentation."
        formatted_docstring = docstring.replace('\n', ' ')
        output += f"Function: '{function.name}'\nDocstring: '{formatted_docstring}'\n\n"

    return output.strip()

def show_function_code(function_name, filename="config.py"):
    """
    Parses a Python file and returns the source code of the specified function.

    Args:
    filename (str): The path to the Python file.
    function_name (str): The name of the function to extract.

    Returns:
    str: The source code of the function or an error message if the function is not found.
    """
    try:
        with open(filename, 'r') as file:
            source = file.read()
            node = ast.parse(source)

        for func in [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]:
            if func.name == function_name:
                return ast.get_source_segment(source, func)

        return f"Function '{function_name}' not found in '{filename}'."
    except FileNotFoundError:
        return f"File '{filename}' not found."
    except Exception as e:
        return f"An error occurred: {e}"

def list_actions(actions):
    '''
    List all actions the model can do
    '''
    space = " "
    actions_str = [ f"   '{action['name'] + space + space.join(action['arguments']) if action['arguments'] else action['name']}' : {action['doc']} " for action in actions]

    return "\n".join(actions_str)


def bootstrap_model(goal):
    actions = [
        {
            'name' : 'list',
            'arguments' : [],
            'doc' : "list all functions in the project",
            'action' : extract_functions_with_doc
        },
        {
            'name' : "show",
            'arguments' : ["function-name"],
            'doc' : 'Shows the code of a function with name "function-name"',
            'action' : show_function_code
        },
        {
            "name" : "modify",
            "arguments" : ["function-name"],
            "doc": "Modify an existing function with name 'function-name'. You will be asked to enter the new code as stdin.",
            "action" : None
        },
        {
            "name" : "create",
            "arguments" : ["function-name"],
            "doc": "Create a new function with the name 'function-name'. You will be asked to enter the new code as stdin.",
            "action" : None
        }
    ]

    history = f"""> list
{extract_functions_with_doc()}
"""



    while True:
        prompt = f"""You are a senior programmer with a lot of expertise in Python and you are tasked to read, understand and then modify the source code of a tool to query language models called shell+ai. 
    
Here is your goal : {goal}

You have access to a special shell-like command interface. This interface that has the following commands available :  
{list_actions(actions)}

Always answer with a valid shell-command that is contained in one line. A line break will exectute the command.

{history}

> """   

        #print("Q:", prompt)
        model_answer = query_model(prompt, stops=["\n"])
        print("A:", "'" + model_answer + "'")
        
        if model_answer.strip():
            arguments = model_answer.split()
            repl_response = ""
            for action in actions:
                if action['name'] == arguments[0]:
                    if len(arguments[1:]) != len(action['arguments']):
                        repl_response = f"Invalid number of arguments for : '{arguments[0]}'"
                    else:
                        try:
                            repl_response = action['actions'](*arguments[1:])
                        except e:
                            repl_response = "An error occured : " + str(e)
            if not repl_response:
                repl_response = f"Invalid command : '{arguments[0]}' "
        
        history = f"""{history}

> {model_answer}
{repl_response}
"""

 


def query_model(prompt, model="", temperature=0.7, stops=["</s>", "Llama:", "User:"]):
    """
    Queries a local server model for a conversational response. 
    Args:
    prompt (str): Input for the model.
    temperature (float): Randomness of the response, default 0.7.
    stops (list): Stopping conditions for the response, default ["</s>", "Llama:", "User:"].

    Returns:
    str: Model's response or error message.
    """

    url = "http://127.0.0.1:8080/completion"
    payload = {
        "stream": False,
        "n_predict": 400,
        "temperature": temperature,
        "stop": stops,
        "repeat_last_n": 256,
        "repeat_penalty": 1.18,
        "top_k": 40,
        "top_p": 0.5,
        "tfs_z": 1,
        "typical_p": 1,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "mirostat": 0,
        "mirostat_tau": 5,
        "mirostat_eta": 0.1,
        "grammar": "",
        "n_probs": 0,
        "image_data": [],
        "cache_prompt": True,
        "slot_id": -1,
        "prompt": prompt
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        response_json = response.json()
        return response_json.get("content", "")
    except requests.RequestException as e:
        return str(e)


def main():
    """
    Main entry point for the program.
    """

    help_message = """This is a utility to query a model. Currently, it has the following functions : 
  ai [-h] [-b] prompt... 

  -h --help : displays this help message
  -b --boot : bootstraps the model, meaning that is modifies its own code to add a requested feature
  prompt : The prompt to send to the language model. If -b is specified, the feature that should be added
"""

    arguments = sys.argv
    if len(arguments) == 1 or '--help' in arguments or '-h' in arguments:
        print(help_message)
    elif arguments[1] == '--boot' or arguments[1] == '-b':
        bootstrap_model(" ".join(arguments[2:]))
    else:
        print(query_model(" ".join(arguments)))

    
main()
