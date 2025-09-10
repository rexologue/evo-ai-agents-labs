Создание MCP-сервера для расчета кредитов и вкладов
==================================================

В этой лабораторной работе вы создадите MCP-сервер, предоставляющий инструменты для расчета графиков выплат по кредитам и вкладам.  
Вы освоите основы разработки MCP-сервисов с использованием фреймворка FastMCP, подготовите Docker-образ и развернете его в облаке |names__company| |names__evo|.  
В результате вы получите навыки интеграции собственных инструментов с AI-агентами и сможете использовать их в автоматизированных сценариях.

Вы будете использовать следующие сервисы:

- :doc:`Artifact Registry <artifact-registry__ug:index>` --- реестр контейнеров для хранения Docker-образов.
- :doc:`AI Agents <ai-agents__ug:index>` --- платформа для создания и управления AI-агентами.
- FastMCP --- фреймворк для создания MCP-серверов.
- Docker --- для сборки и распространения сервиса.

Шаги:

#. :ref:`Подготовьте инфраструктуру <mcp-server__step1>`.
#. :ref:`Создайте MCP-сервер <mcp-server__step2>`.
#. :ref:`Соберите и загрузите Docker-образ <mcp-server__step3>`.
#. :ref:`Создайте MCP-сервер в облаке <mcp-server__step4>`.
#. :ref:`Создайте агента с MCP-тулами <mcp-server__step5>`.

|section-titles__before-work|
-----------------------------

#. 
   .. include:: /../../_warehouse/console.rsti
      :start-after: {{start-after console__quickstart-all}}
      :end-before: {{end-before console__quickstart-all}}

.. _mcp-server__step1:

1. Подготовьте инфраструктуру
-----------------------------

На этом шаге вы создадите реестр и репозиторий в Artifact Registry для хранения Docker-образа вашего MCP-сервера.

#. :doc:`Создайте реестр <artifact-registry__ug:topics/guides__create-registry>` в сервисе Artifact Registry.
#. :doc:`Создайте репозиторий <artifact-registry__ug:topics/guides__create-repository>` в созданном реестре для хранения образа MCP-сервера.

.. _mcp-server__step2:

2. Создайте MCP-сервер
----------------------

На этом шаге вы реализуете базовую структуру MCP-сервера с инструментами расчета кредитов и вкладов.

#. Создайте файл ``src/main.py`` со следующим содержимым:

   .. code-block:: python

      import os
      from fastmcp import FastMCP

      mcp = FastMCP("Finance Schedules")

      @mcp.tool
      def loan_schedule_annuity(principal: float, annual_rate_percent: float, months: int) -> dict:
          """
          Рассчитывает график аннуитетных платежей по кредиту.

          Args:
              principal (float): Сумма кредита (> 0).
              annual_rate_percent (float): Годовая процентная ставка (0 < rate <= 100).
              months (int): Срок кредита в месяцах (> 0).

          Returns:
              Dict[str, Any]: Словарь с ключами 'summary' и 'schedule'.
                  - summary: Общая информация по кредиту.
                  - schedule: Список ежемесячных платежей.

          Raises:
              ValueError: Если параметры выходят за допустимые границы.
          """
          if principal <= 0:
              raise ValueError("principal должно быть положительным числом.")
          if not (0 < annual_rate_percent <= 100):
              raise ValueError("annual_rate_percent должно быть в диапазоне (0, 100].")
          if months <= 0:
              raise ValueError("months должно быть положительным числом.")

          monthly_rate = annual_rate_percent / 100 / 12
          annuity_payment = principal * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
          
          schedule = []
          remaining_principal = principal
          total_interest = 0

          for month in range(1, months + 1):
              interest_payment = remaining_principal * monthly_rate
              principal_payment = annuity_payment - interest_payment
              remaining_principal -= principal_payment
              total_interest += interest_payment

              schedule.append({
                  "month": month,
                  "payment": round(annuity_payment, 2),
                  "principal": round(principal_payment, 2),
                  "interest": round(interest_payment, 2),
                  "remaining": round(max(remaining_principal, 0), 2)
              })

          summary = {
              "total_payment": round(annuity_payment * months, 2),
              "total_interest": round(total_interest, 2)
          }

          return {"summary": summary, "schedule": schedule}

      if __name__ == "__main__":
          mcp.run(
              transport="sse",
              host="0.0.0.0",
              port=os.getenv("PORT", 8000)
          )

#. Реализуйте дополнительные инструменты по необходимости, следуя тем же принципам.

.. _mcp-server__step3:

3. Соберите и загрузите Docker-образ
------------------------------------

На этом шаге вы подготовите Docker-образ вашего MCP-сервера и загрузите его в Artifact Registry.

#. Создайте файл ``Dockerfile`` в корне проекта:

   .. code-block:: dockerfile

      FROM python:3.11-slim

      WORKDIR /app

      COPY requirements.txt .
      RUN pip install --no-cache-dir -r requirements.txt

      COPY src/ ./src/

      EXPOSE 8000

      CMD ["python", "src/main.py"]

#. Создайте файл ``requirements.txt``:

   .. code-block:: text

      fastmcp>=0.1.0

#. Выполните аутентификацию в Artifact Registry:

   .. code-block:: bash

      gcloud auth configure-docker cloudru-labs.cr.cloud.ru

#. Соберите Docker-образ:

   .. code-block:: bash

      docker buildx build --platform linux/amd64 -t mcp-finance .

#. Присвойте образу тег:

   .. code-block:: bash

      docker tag mcp-finance:latest cloudru-labs.cr.cloud.ru/<REPO_NAME>:v1.0.0

   Где:

   - <REPO_NAME> --- имя репозитория, созданного на шаге 1.

#. Загрузите образ в репозиторий:

   .. code-block:: bash

      docker push cloudru-labs.cr.cloud.ru/<REPO_NAME>:v1.0.0

.. _mcp-server__step4:

4. Создайте MCP-сервер в облаке
-------------------------------

На этом шаге вы зарегистрируете MCP-сервер в облаке |names__company| |names__evo|.

#. В личном кабинете перейдите в раздел :menuselection:`AI --> AI Agents`.
#. Нажмите :guilabel:`Создать MCP-сервер`.
#. Укажите параметры:

   - :guilabel:`Название`: Finance MCP Server.
   - :guilabel:`Docker-образ`: cloudru-labs.cr.cloud.ru/<REPO_NAME>:v1.0.0.
   - :guilabel:`Порт`: 8000.

#. Нажмите :guilabel:`Создать`.

Убедитесь, что сервер успешно создан и отображается в списке с состоянием "Активен".

.. _mcp-server__step5:

5. Создайте агента с MCP-тулами
-------------------------------

На этом шаге вы создадите AI-агента, который будет использовать инструменты вашего MCP-сервера.

#. В личном кабинете перейдите в раздел :menuselection:`AI --> AI Agents`.
#. Нажмите :guilabel:`Создать агента`.
#. Укажите параметры:

   - :guilabel:`Название`: Finance Agent.
   - :guilabel:`MCP-сервер`: Finance MCP Server (выбранный на предыдущем шаге).

#. Нажмите :guilabel:`Создать`.

Убедитесь, что агент создан и имеет доступ к инструментам.

|section-titles__next|
----------------------

В ходе лабораторной работы вы создали MCP-сервер с инструментами финансовых расчетов, подготовили и загрузили Docker-образ, а также интегрировали сервер с AI-агентом.  

Узнавайте больше о работе с сервисами и получайте практические навыки управления облаком, выполняя :doc:`лабораторные работы <../index>`.
