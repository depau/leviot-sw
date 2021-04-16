from leviot import conf, VERSION

base = """<!DOCTYPE html>
<html>
<head>
<meta http-equiv="refresh" content="5">
<title>{title}</title>
</head>
<body>
<h1>{title}</h1>
{content}
<div style="font-style: italic">Powered by LevIoT v""" + VERSION + """</div>
</body>
</html>
"""

index = base.format(
    title=conf.hostname + " - Basic comtrol",
    content="""
    <div>
        <ul>
            <li>Power: {power} (turn <a href="/priv-api/on">ON</a>, <a href="/priv-api/off">OFF</a>)</li>
            <li>Fan speed: {speed} (set to <a href="/priv-api/fan?speed=0">Night</a>, <a href="/priv-api/fan?speed=1"
            >I</a>, <a href="/priv-api/fan?speed=2">II</a>, <a href="/priv-api/fan?speed=3">III</a>)</li>
        </ul>
    </div>
    """)
