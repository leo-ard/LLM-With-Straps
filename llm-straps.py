import requests
import ast
import os

system_prompt = lambda x: {'role': 'system', 'content': x}
user_prompt = lambda x: {'role': 'user', 'content': x}
assistant_prompt = lambda x: {'role': 'assistant', 'content': x}

def extract_functions_with_doc(node, prompt, stdin):
    """Extracts functions and their docstrings from given a Python file, formatted for language model parsing.

    Args:
        filename (str): path to the Python file

    Returns:
        str: A structured string containing function names and docstrings from all files, formatted for language model parsing.
    """
    output = ''
    functions = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]
    for function in functions:
        docstring = ast.get_docstring(function) or 'No documentation.'
        formatted_docstring = docstring.replace('\n', ' ')
        output += f"Function: '{function.name}'\nDocstring: '{formatted_docstring}'\n\n"
    return (output.strip(), prompt)

def show_function_code(node, prompt, stdin, function_name):
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
            return (ast.unparse(func), prompt)
    return (f"Function '{function_name}' not found.", prompt)

def create_function(node: ast, prompt, function_code: str, function_name):
    functions = [n.name for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]
    if function_name in functions:
        return f"Function '{function_name}' already exists"
    function_ast = ast.parse(function_code)
    node.body.insert(function_ast.body, -2)
    return ('Function created', prompt)

def apply_patch(original, patch):
    import tempfile
    import subprocess
    with tempfile.NamedTemporaryFile('w+', delete=False) as orig_file, tempfile.NamedTemporaryFile('w+', delete=False) as patch_file:
        orig_file.write(original)
        orig_file.close()
        patch_file.write(patch)
        patch_file.close()
        subprocess.run(['patch', '-l', '--fuzz=3', orig_file.name, patch_file.name], check=True, capture_output=True, text=True)
        with open(orig_file.name, 'r') as f:
            return f.read()

def modify_function(node: ast.Module, prompt: [str], new_function_body: str, function_name: str):
    if not new_function_body.strip():
        return ("Error : Nothing specified to stdin. Please call 'modify <function-name>' with only the new body of the function.", prompt)
    functions = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]
    found = False
    for function in functions:
        if function.name == function_name:
            index = node.body.index(function)
            new_function_module = ast.parse(new_function_body)
            new_function_definition = [n for n in ast.walk(new_function_module) if isinstance(n, ast.FunctionDef) and n.name == function_name]
            if len(new_function_definition) > 1:
                return ('Error : To many functions defined', prompt)
            if len(new_function_definition) == 0:
                return (f'Error : No functions with name {function_name} defined', prompt)
            node.body[index] = new_function_definition[0]
            found = True
    if not found:
        return (f"Error : no function named '{function_name}'", prompt)
    return ('Function modified', prompt)

def list_actions(actions):
    """
    List all actions the model can do
    """
    space = ' '
    actions_str = [f"   '{(action['name'] + space + space.join(action['arguments']) if action['arguments'] else action['name'])}' : {action['doc']} " for action in actions]
    return '\n'.join(actions_str)

def display_prompt(messages):
    """
    Utility function to display the prompt (used for debugging)
    """
    for message in messages:
        print(message['role'].upper() + ': ' + message['content'] + '\n')

def bootstrap_model(goal, debug=False):
    actions = [{'name': 'list', 'arguments': [], 'doc': 'list all functions in the project', 'action': extract_functions_with_doc}, {'name': 'show', 'arguments': ['<function-name>'], 'doc': 'Shows the code of a function with name "function-name"', 'action': show_function_code}, {'name': 'modify', 'arguments': ['<function-name>'], 'doc': "Modify an existing function with name 'function-name'. Follow the command with valid python code containing only the function and its new body.", 'action': modify_function}, {'name': 'create', 'arguments': ['<function-name>'], 'doc': "Create a new function with the name 'function-name'. Follow the command with valid python code containing only the function and its body.", 'action': create_function}, {'name': 'exit', 'arguments': ['<message>'], 'doc': 'Exit and displays the message to the user', 'action': None}]
    node = None
    with open(__file__, 'r') as file:
        node = ast.parse(file.read())
    if debug:
        print(f'Debugging bootstrap_model with goal: {goal}')
    prompt = [system_prompt(f'You are a senior programmer with a lot of expertise in Python and you are tasked to read, understand and then modify the source code of a tool to query language models called shell+ai. \nHere is your goal : {goal}\nYou have access to a shell with the following commands : \n{list_actions(actions)}\n\nAlways answer with a valid command.'), assistant_prompt('list'), user_prompt(extract_functions_with_doc(node, None, '')[0])]
    while True:
        model_answer, prompt = query_model(prompt, debug=debug)
        if model_answer:
            model_answer: str = model_answer.splitlines()
            first_line = model_answer[0]
            stdin = '\n'.join(model_answer[1:]) if len(model_answer) > 1 else ''
            arguments = first_line.split()
            repl_response = ''
            if arguments[0] == 'exit':
                print(' '.join(arguments[1:]))
                break
            for action in actions:
                if action['name'] == arguments[0]:
                    if len(arguments[1:]) != len(action['arguments']):
                        repl_response = f"Invalid number of arguments for : '{arguments[0]}'"
                    else:
                        repl_response, prompt = action['action'](node, prompt, stdin, *arguments[1:])
            if not repl_response:
                repl_response = f"Invalid command : '{arguments[0]}' "
        prompt += [user_prompt(repl_response)]
    if debug:
        print('bootstrap_model execution finished.')
    self_name = os.path.basename(__file__)[:-3]
    self_name_prefix = self_name + '__'
    files = os.listdir('.')
    hightest_number = 0
    for file in files:
        if file.startswith(self_name_prefix):
            try:
                number = int(file[len(self_name_prefix):-3])
            except ValueError:
                number = 0
            hightest_number = max(number, hightest_number)
    new_filename = f'{self_name}__{hightest_number + 1}.py'
    print(f'Output written to {new_filename}')
    with open(new_filename, 'w') as file:
        file.write(ast.unparse(node))

def post_process_remove_markdown(message):
    return '\n'.join(filter(lambda line: not line.startswith('```'), message.splitlines()))

def query_model(messages, model='gpt-4-1106-preview', temperature=1, stops=[], debug=True):
    """
    Queries a local server model for a conversational response. 
    Args:
    messages (list): Input messages for the model.
    model (str): Model identifier, default 'gpt-4-1106-preview'.
    temperature (float): Randomness of the response, default 0.7.
    stops (list): Stopping conditions for the response, default ["</s>", "Llama:", "User:"].
    debug (bool): Enables debug information if set to True.

    Returns:
    str: Model's response or error message.
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print('Error: cannot find open ai key in environnement variables. Please set OPENAI_API_KEY accordingly.')
        exit(1)
    url = 'https://api.openai.com/v1/chat/completions'
    payload = {'temperature': temperature, 'stop': stops, 'messages': messages, 'model': model, 'max_tokens': 2048}
    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer ' + api_key}
    if debug:
        print('============= DEBUG: DISPLAYING QUERY PAYLOAD ============')
        display_prompt(messages)
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    response_json = response.json()
    message_answer = response_json['choices'][0]['message']
    message_answer = {'role': message_answer['role'], 'content': post_process_remove_markdown(message_answer['content'])}
    return (message_answer['content'], messages + [message_answer])

def main():
    """
    Main entry point for the program with --debug/-d argument.
    """
    import argparse
    parser = argparse.ArgumentParser(description='Query a model and optionally display debug information.')
    parser.add_argument('prompt', nargs='+', help='The prompt(s) to send to the language model.')
    parser.add_argument('--boot', '-b', action='store_true', help='Bootstraps the model.')
    parser.add_argument('--debug', '-d', action='store_true', help='Enables debug output.')
    args = parser.parse_args()
    if args.boot:
        bootstrap_model(' '.join(args.prompt), debug=args.debug)
    else:
        response, _ = query_model(messages=args.prompt, debug=args.debug)
        print(response)
main()