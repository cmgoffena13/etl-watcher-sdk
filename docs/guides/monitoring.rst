Monitoring
==========

This guide will show you how to trigger monitoring tasks within the Watcher framework.

Trigger Timeliness Check
------------------------

You can trigger a timeliness check by using the `trigger_timeliness_check` method.

.. code-block:: python

    from watcher import Watcher

    watcher = Watcher("https://api.watcher.example.com")

    watcher.trigger_timeliness_check(lookback_minutes=60)

Trigger Freshness Check
------------------------

You can trigger a freshness check by using the `trigger_freshness_check` method.

.. code-block:: python

    from watcher import Watcher

    watcher = Watcher("https://api.watcher.example.com")

    watcher.trigger_freshness_check()

Trigger Celery Queue Check
--------------------------

You can trigger a celery queue check by using the `trigger_celery_queue_check` method.

.. code-block:: python

    from watcher import Watcher

    watcher = Watcher("https://api.watcher.example.com")

    watcher.trigger_celery_queue_check()