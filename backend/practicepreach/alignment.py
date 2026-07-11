import logging

from langchain_core.prompts import ChatPromptTemplate


logger = logging.getLogger(__name__)

tone_analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert at analyzing political texts and comparing their tone and style.
Your task is to analyze how the tone differs between party manifestos and parliamentary speeches on the same topic.

Analyze:
- Tone differences (formal vs. informal, assertive vs. cautious, etc.)
- Language style (academic vs. conversational, abstract vs. concrete)
- Rhetorical strategies (promises vs. explanations, vision vs. reality)
- Emotional register (passionate vs. measured, optimistic vs. pragmatic)
- Level of detail and specificity
- Use of technical vs. accessible language
- Coverage of topics: Are the same topics covered in speech as they are in manifestos

Take into account that a manifesto is always written and speeches are spoken. Therefore the baseline language is different.
Please judge if the speech reflects well, what the party promised to do. Give only one of these labels:
'Does not align well with manifesto', 'Aligns partly with manifesto', 'Aligns mostly with manifesto', 'Aligns well with manifesto'.

"""),
    ("human", """Compare following manifesto excerpts and parliamentary speeches:

MANIFESTO EXCERPTS:
{manifesto_texts}

PARLIAMENTARY SPEECHES:
{speech_texts}

Give me an alignment label. Only one and without explanation.""")
])


def analyze_tone_differences(
    manifesto: str,
    speech: str,
    model
) -> dict:
    """
    Analyze tone differences between manifesto and speech chunks from JSON files.
    """

    # Create prompt
    prompt = tone_analysis_prompt.invoke({
        "manifesto_texts": manifesto,
        "speech_texts": speech
    })

    # Get analysis from LLM
    logger.info("Scoring alignment with LLM...")
    response = model.invoke(prompt)

    return  response.content
