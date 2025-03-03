import logging
import tempfile
import zipfile
import time
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from config import logger

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_username, proxy_password, scheme='http'):
    """
    Creates a Chrome extension (as a .zip file) to handle proxy authentication.
    Returns the file path to the generated extension.
    """
    try:
        logger.info("Starting proxy authentication extension creation.")

        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Chrome Proxy",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            }
        }
        """
        background_js = f"""
        var config = {{
            mode: "fixed_servers",
            rules: {{
              singleProxy: {{
                scheme: "{scheme}",
                host: "{proxy_host}",
                port: parseInt({proxy_port})
              }},
              bypassList: ["localhost"]
            }}
          }};

        chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

        function callbackFn(details) {{
            return {{
                authCredentials: {{
                    username: "{proxy_username}",
                    password: "{proxy_password}"
                }}
            }};
        }}

        chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {{urls: ["<all_urls>"]}},
            ["blocking"]
        );
        """

        plugin_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        with zipfile.ZipFile(plugin_file, 'w') as zp:
            zp.writestr("manifest.json", manifest_json.strip())
            zp.writestr("background.js", background_js.strip())
        plugin_file.close()

        logger.info("Successfully created proxy authentication extension at: %s", plugin_file.name)
        return plugin_file.name

    except Exception as e:
        logger.critical("Failed to create proxy authentication extension: %s", e, exc_info=True)
        return None

def setup_driver(browser_url="",
                 proxy_host=None,
                 proxy_port=None,
                 proxy_username=None,
                 proxy_password=None,
                 proxy_scheme="http"):
    """
    Initialize a Chrome webdriver with options optimized for speed.
    If proxy settings are provided, the proxy is configured.
    """
    logger.info("Starting driver setup.")

    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.page_load_strategy = "eager"

    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.managed_default_content_settings.plugins": 2,
    }
    options.add_experimental_option("prefs", prefs)

    # Configure proxy if details are provided
    if proxy_host and proxy_port:
        try:
            if proxy_username and proxy_password:
                proxy_extension = create_proxy_auth_extension(proxy_host, proxy_port, proxy_username, proxy_password, scheme=proxy_scheme)
                options.add_extension(proxy_extension)
                logger.info("Using proxy authentication extension for %s:%s", proxy_host, proxy_port)
            else:
                options.add_argument(f"--proxy-server={proxy_scheme}://{proxy_host}:{proxy_port}")
                logger.info("Configured proxy: %s:%s using scheme %s", proxy_host, proxy_port, proxy_scheme)
        except Exception as e:
            logger.critical("Failed to configure proxy: %s", e, exc_info=True)
            raise

    try:
        if browser_url:
            logger.info("Initializing remote WebDriver at URL: %s", browser_url)
            driver = webdriver.Remote(command_executor=browser_url, options=options)
        else:
            logger.info("Initializing local Chrome WebDriver.")
            driver = webdriver.Chrome(options=options)
        logger.info("WebDriver initialized successfully.")
    except WebDriverException as e:
        logger.critical("WebDriver initialization failed.", exc_info=True)
        raise e

    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd(
            "Network.setBlockedURLs",
            {"urls": [
                "*googleapis.com/maps*",
                "*googleapis.com/vt?*",
                "*maps.gstatic.com*",
                "*.jpg", "*.jpeg", "*.png", "*.gif",
                "*.css", "*.woff", "*.woff2", "*.ttf",
                "*google-analytics.com*", "*adservice.google.com*",
                "*doubleclick.net*", "*facebook.net*"
            ]}
        )
        logger.info("CDP block list configured successfully.")
    except Exception as e:
        logger.warning("Error setting CDP block list: %s", e, exc_info=True)

    driver.set_page_load_timeout(20)
    logger.info("WebDriver setup completed successfully.")
    return driver
