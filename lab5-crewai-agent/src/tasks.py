"""Определение задач для CrewAI crew."""
from crewai import Task


def create_tasks(agents):
    """Создает задачи для crew на основе агентов."""
    coordinator, executor = agents
    
    # Задача для координатора - анализировать запрос
    analyze_task = Task(
        description="Проанализируй запрос пользователя и определи, какие инструменты нужны для его выполнения",
        agent=coordinator,
        expected_output="Список необходимых инструментов и план выполнения задачи"
    )
    
    # Задача для исполнителя - выполнить запрос
    execute_task = Task(
        description="Выполни запрос пользователя используя доступные инструменты",
        agent=executor,
        expected_output="Результат выполнения запроса с детальным ответом"
    )
    
    return [analyze_task, execute_task]


