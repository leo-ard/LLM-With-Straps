import sys
import requests
import ast
import os
import pprint
import shutil

pp = pprint.PrettyPrinter(indent=4)
system_prompt = lambda x : {'role' : 'system', 'content' : x}
user_prompt = lambda x : {'role' : 'user', 'content' : x}
assistant_prompt = lambda x : {'role' : 'assistant', 'content' : x}

def extract_functions_with_doc(node, prompt):
    """Extracts functions and their docstrings from given a Python file, formatted for language model parsing.

    Args:
        filename (str): path to the Python file

    Returns:
        str: A structured string containing function names and docstrings from all files, formatted for language model parsing.
    """
    output = ""

    functions = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]

    for function in functions:
        docstring = ast.get_docstring(function) or "No documentation."
        formatted_docstring = docstring.replace('\n', ' ')
        output += f"Function: '{function.name}'\nDocstring: '{formatted_docstring}'\n\n"

    return output.strip(), prompt

def show_function_code(node, prompt, function_name):
    """
    Parses a Python file and returns the source code of the specified function.

    Args:
    filename (str): The path to the Python file.
    function_name (str): The name of the function to extract.

    Returns:
    str: The source code of the function or an error message if the function is not found.
    """
    for func in [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]:
        if func.name == function_name:
            return ast.unparse(func), prompt

    return f"Function '{function_name}' not found.", prompt

def create_function(node : ast, prompt, function_name):

    functions = [n.name for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]
    if function_name in functions:
        return f"Function '{function_name}' already exists"

    # prompt += [
    #     user_prompt("Function docstring :")
    # ]

    # docstring, prompt = query_model(prompt)

    prompt += [
        user_prompt("Input code :")
    ]

    function_content, prompt = query_model(prompt)

    #docstring_ast = ast.Expr(value=ast.Constant(s=docstring))
    function_ast = ast.parse(function_content)
    #function_ast.body[0].body.insert(0, docstring_ast)

    node.body.extend(function_ast.body)
    
    return "Function created", prompt

def modify_function(node, prompt, function_name):
    functions = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]

    found = False
    for function in functions:
        if function.name == function_name:
            node.body.remove(function)
            found = True
            

    if not found:
        return f"Error : no function named '{function_name}'"

    return create_function(node, prompt, function_name)


def list_actions(actions):
    '''
    List all actions the model can do
    '''
    space = " "
    actions_str = [ f"   '{action['name'] + space + space.join(action['arguments']) if action['arguments'] else action['name']}' : {action['doc']} " for action in actions]

    return "\n".join(actions_str)

def display_prompt(messages):
    '''
    Utility function to display the prompt (used for debugging)
    '''

    for message in messages:
        print(message['role'].upper() + ": " + message['content'] + "\n")


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
            'arguments' : ["<function-name>"],
            'doc' : 'Shows the code of a function with name "function-name"',
            'action' : show_function_code
        },
        {
            "name" : "modify",
            "arguments" : ["<function-name>"],
            "doc": "Modify an existing function with name 'function-name'. You will be asked to enter the new code as stdin.",
            "action" : modify_function 
        },
        {
            "name" : "create",
            "arguments" : ["<function-name>"],
            "doc": "Create a new function with the name 'function-name'. You will be asked to enter the new code as stdin.",
            "action" : create_function
        },
        {
            "name" : "exit",
            "arguments" : ["<message>"],
            "doc": "Exit and displays the message to the user",
            "action" : None
        }
    ]

    node = None
    with open("config.py", "r") as file:
        node = ast.parse(file.read())
    

    prompt = [
        system_prompt(
            "You are a senior programmer with a lot of expertise in Python and you are " 
            "tasked to read, understand and then modify the source code of a tool to query "
            "language models called shell+ai. \n"
            f"Here is your goal : {goal}\n"
            "You have access to a special shell-like command interface. This interface has the"
            f"following command available : \n{list_actions(actions)}" 
            "\n\nAlways answer with a valid shell-command that is contained in one line. A line break"
            " will exectute the command."
        ),
        assistant_prompt("list"), 
        user_prompt(extract_functions_with_doc(node, None)[0])
    ]

    while True:
        model_answer, prompt = query_model(prompt, stops=["\n"])
        
        if model_answer.strip():
            arguments = model_answer.split()
            repl_response = ""
            if arguments[0] == "exit":
                print(" ".join(arguments[1:]))
                break

            for action in actions:
                if action['name'] == arguments[0]:
                    if len(arguments[1:]) != len(action['arguments']):
                        repl_response = f"Invalid number of arguments for : '{arguments[0]}'"
                    else:
                        #try:
                            repl_response, prompt = action['action'](node, prompt, *arguments[1:])
                        #except Exception as e:
                        #    repl_response = "An error occured : " + str(e)
            if not repl_response:
                repl_response = f"Invalid command : '{arguments[0]}' "
        
        prompt += [
            user_prompt(repl_response)
        ]
    

    print("The file is now accessible as config.py")
    files = os.listdir(".")
    hightest_number = 0
    for file in files:
        if file.startswith("config_"):
            hightest_number = max(int(file[7:-3]), hightest_number)
    
    new_filename = f"config_{hightest_number+1}.py"
    with open(new_filename, "w") as file:
        file.write(ast.unparse(node))


 


def query_model(messages, model="gpt-3.5-turbo", temperature=1, stops=[]):
    """
    Queries a local server model for a conversational response. 
    Args:
    prompt (str): Input for the model.
    temperature (float): Randomness of the response, default 0.7.
    stops (list): Stopping conditions for the response, default ["</s>", "Llama:", "User:"].

    Returns:
    str: Model's response or error message.
    """

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: cannot find open api key in environnement variables. Please set OPENAI_API_KEY accordingly.")
        exit(1)

    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "temperature": temperature,
        "stop": stops,
        "messages": messages,
        "model" : model,
        "max_tokens" : 2048
    }

    headers = {
        "Content-type" : "application/json",
        "Authorization" : "Bearer " + api_key 
    }

    print("============= DISPLAYING PROMPT ============")
    display_prompt(messages)

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    response_json = response.json()
    message_answer = response_json['choices'][0]['message']

    print("A:", "'" + message_answer['content'] + "'")

    input()

    return message_answer['content'], messages + [message_answer]


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
