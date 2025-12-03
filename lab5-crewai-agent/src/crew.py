"""Определение CrewAI crew."""
import os
from crewai import Crew, Process
from agents import create_crew_agents
from tasks import create_tasks


def create_crew(mcp_urls: str = None):
    """Создает CrewAI crew с агентами и задачами."""
    # Создаем агентов
    agents = create_crew_agents(mcp_urls)
    
    # Создаем задачи
    tasks = create_tasks(agents)
    
    # Создаем crew
    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,  # Последовательное выполнение задач
        verbose=True,
    )
    
    return crew


