
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from execution import nlu

text = "open sample.xlsx file and add a new row roll no 51 and first name is raj and last name is kumar and gender is male and country is india and age is 21 and date is 14/10/2004 and is iss 1410"
print(f"Input: {text}")
commands = nlu.extract_commands(text)
for cmd in commands:
    print(f"Action: {cmd.action}")
    print(f"Target: {cmd.target}")
    print(f"Context: {cmd.context}")
    print("-" * 20)
