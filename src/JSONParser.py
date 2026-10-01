import pyjson5

with open("v2x-project\inputFiles\SPaT.json5", "r") as file:
    project = pyjson5.load(file)

print(project)
