import re
# import spacy
# from spacy.matcher import Matcher

def find_skills(skill_names:dict, prompt: str) -> list[str]:
    pattern = re.compile(r'\b(' + '|'.join([re.escape(skill) for skill in skill_names]) + r')\b', re.IGNORECASE)
    matches = pattern.findall(prompt)
    return set(matches)

def find_employment_types(prompt:str)  -> list[str]: 
    employment_types=["full","part"]
    return [ type for type in employment_types if type in prompt]

#explore an nlp solution to parse budget better

# nlp = spacy.load("en_core_web_sm")

# def find_budget(prompt:str) -> list[int|str]:
#     doc = nlp(prompt)

#     # Initialize spaCy Matcher
#     matcher = Matcher(nlp.vocab)

#     # Define patterns to match prices
#     number_patterns = [
#         {"LIKE_NUM": True},  # Matches tokens that look like a number
#         {"IS_PUNCT": True, "OP": "?"},  # Matches optional punctuation (for decimals)
#         {"LIKE_NUM": True, "OP": "?"}  # Matches optional second number (for decimals),
#     ]

#     # Add patterns to the matcher
#     matcher.add("budget",[number_patterns])

#     # Find matches in the document
#     matches = matcher(doc)

#     # Extract matched phrases
#     prices = []
#     for _, start, end in matches:
#         span = doc[start:end]
#         prices.append(span.text)

#     return prices

def find_budget(prompt:str)  -> list[int|str]:
    return re.findall(r'\d+', prompt)