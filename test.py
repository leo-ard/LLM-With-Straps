def modify_function(node : ast.Module, prompt : [str], patch_file : str, function_name : str):
    import subprocess
    functions = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]

    found = False
    for function in functions:
        if function.name == function_name:
            index = node.body.index(function)

            try:
                patched_code = apply_patch(ast.unparse(function), patch_file)
            except subprocess.CalledProcessError as e:
                return "Error with patch : " + e.stdout + e.stderr, prompt

            patched_function_node = ast.parse(patched_code).body[0]
            if not isinstance(patched_function_node, ast.FunctionDef):
                return f"Error: Patch did not result in a valid function definition", prompt
            node.body[index] = patched_function_node
            print (ast.unparse(patched_function_node))

            found = True

    if not found:
        return f"Error : no function named '{function_name}'", prompt

    return "Function modified", prompt
