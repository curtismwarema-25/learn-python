from django.db import migrations


PATHWAY = {
    'slug': 'ai-awareness',
    'title': 'AI Awareness',
    'description': (
        'A practical first journey for understanding what AI systems do, '
        'where their outputs come from, and how to use them responsibly.'
    ),
    'outcome': (
        'Explain a simple AI flow and identify one task where AI may or may not help.'
    )
}

UNITS = [
    {
        'title': 'Start with the problem',
        'description': 'Describe the human goal before choosing a tool.',
        'lessons': [
            (
                'Name the task',
                'Turn a broad frustration into one clear task.',
                'AI is easier to evaluate when the task is concrete. Start with what a person is trying to do, who it helps, and what a useful result would look like. A tool should serve that goal, not define it.',
                'Write one everyday task you would like to improve and describe what a good result would be.',
            ),
            (
                'Separate the pattern from the tool',
                'Recognize a repeatable pattern before selecting technology.',
                'Many tasks contain a pattern: summarize, classify, compare, draft, explain, or transform. Naming the pattern helps you compare possible approaches and notice when a tool is unnecessary.',
                'What pattern best describes your task? Give one reason that a non-AI approach might still be useful.',
            ),
        ]
    },
    {
        'title': 'Understand the flow',
        'description': 'Build a useful mental model of data, models, inputs, and outputs.',
        'lessons': [
            (
                'How systems are prepared',
                'Distinguish preparing a model from using a trained model.',
                'A simplified preparation flow selects and prepares examples, adjusts or trains a model, and evaluates the result. Different systems use different methods, but a normal prompt does not automatically retrain the model.',
                'In your own words, what is the difference between preparing a system and using a prepared system?',
            ),
            (
                'How systems are used',
                'Describe the input, context, output, and review loop.',
                'When using a trained system, people provide an input and sometimes context, receive an output, and review it before deciding what to do. The review step keeps responsibility with the human.',
                'Describe one check you would perform before using an AI-generated result.',
            ),
        ]
    },
    {
        'title': 'Choose responsibly',
        'description': 'Decide where assistance is useful and how to verify the result.',
        'lessons': [
            (
                'Find the useful boundary',
                'Identify where assistance helps and where human judgment must remain.',
                'AI can help with drafting, organizing, comparing, and exploring ideas. It may be unsuitable for decisions that need private information, domain expertise, accountability, or guaranteed accuracy without additional controls.',
                'For your task, where could assistance help, and where should a person remain fully responsible?',
            ),
            (
                'Make a small experiment',
                'Define a testable improvement instead of chasing more output.',
                'A good first experiment has a baseline, a small change, and a way to compare results. Record what improved, what became worse, and what you would change next.',
                'State the small experiment you would run, the baseline you would compare against, and one risk you would watch.',
            ),
        ]
    }
]


def seed_pathway(apps, schema_editor):
    Pathway = apps.get_model('learning', 'LearningPathway')
    Unit = apps.get_model('learning', 'LearningUnit')
    Lesson = apps.get_model('learning', 'LearningLesson')
    Activity = apps.get_model('learning', 'LearningActivity')
    pathway = Pathway.objects.create(published=True, **PATHWAY)
    for unit_position, unit_data in enumerate(UNITS, start=1):
        unit = Unit.objects.create(
            pathway=pathway,
            position=unit_position,
            title=unit_data['title'],
            description=unit_data['description']
        )
        for lesson_position, lesson_data in enumerate(unit_data['lessons'], start=1):
            title, objective, body, prompt = lesson_data
            lesson = Lesson.objects.create(
                unit=unit,
                position=lesson_position,
                title=title,
                objective=objective,
                body=body,
                estimated_minutes=10
            )
            Activity.objects.create(lesson=lesson, prompt=prompt)


def remove_pathway(apps, schema_editor):
    apps.get_model('learning', 'LearningPathway').objects.filter(
        slug=PATHWAY['slug']
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('learning', '0001_initial')]
    operations = [migrations.RunPython(seed_pathway, remove_pathway)]
