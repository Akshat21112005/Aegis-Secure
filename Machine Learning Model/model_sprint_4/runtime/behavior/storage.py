from playwright.async_api import Page


async def collect_storage(page: Page):

    await page.wait_for_load_state("domcontentloaded")

    await page.wait_for_timeout(2000)

    cookies = await page.context.cookies()

    cookie_summary = {

        "count":len(cookies),

        "secure":0,

        "http_only":0,

        "session":0,

        "persistent":0,

        "same_site":{

            "Strict":0,

            "Lax":0,

            "None":0

        },

        "domains":[]

    }

    domains = set()

    for cookie in cookies:

        if cookie.get("secure"):

            cookie_summary["secure"] += 1

        if cookie.get("httpOnly"):

            cookie_summary["http_only"] += 1

        if cookie.get("expires",-1) == -1:

            cookie_summary["session"] += 1

        else:

            cookie_summary["persistent"] += 1

        same_site = cookie.get("sameSite")

        if same_site in cookie_summary["same_site"]:

            cookie_summary["same_site"][same_site] += 1

        domains.add(

            cookie.get("domain","")

        )

    cookie_summary["domains"] = sorted(

        list(domains)

    )

    local_storage = await page.evaluate(

        """

        () => {

            let size = 0;

            const keys = [];

            for(let i=0;i<localStorage.length;i++){

                const key = localStorage.key(i);

                const value = localStorage.getItem(key);

                keys.push(key);

                size += key.length;

                if(value)

                    size += value.length;

            }

            return{

                count:localStorage.length,

                keys:keys,

                size:size

            };

        }

        """

    )

    session_storage = await page.evaluate(

        """

        () => {

            let size = 0;

            const keys = [];

            for(let i=0;i<sessionStorage.length;i++){

                const key = sessionStorage.key(i);

                const value = sessionStorage.getItem(key);

                keys.push(key);

                size += key.length;

                if(value)

                    size += value.length;

            }

            return{

                count:sessionStorage.length,

                keys:keys,

                size:size

            };

        }

        """

    )

    indexed_db = await page.evaluate(

        """

        async () => {

            if(!indexedDB.databases){

                return{

                    supported:false,

                    count:0,

                    databases:[]

                };

            }

            const dbs = await indexedDB.databases();

            return{

                supported:true,

                count:dbs.length,

                databases:dbs.map(

                    db=>db.name

                )

            };

        }

        """

    )

    cache_api = await page.evaluate(

        """

        async () => {

            if(!window.caches){

                return{

                    supported:false,

                    count:0,

                    caches:[]

                };

            }

            const names = await caches.keys();

            return{

                supported:true,

                count:names.length,

                caches:names

            };

        }

        """

    )

    service_worker = await page.evaluate(

        """

        async () => {

            if(!navigator.serviceWorker){

                return{

                    supported:false,

                    registered:false,

                    count:0,

                    scopes:[]

                };

            }

            const registrations = await navigator.serviceWorker.getRegistrations();

            return{

                supported:true,

                registered:registrations.length>0,

                count:registrations.length,

                scopes:registrations.map(

                    r=>r.scope

                ),

                scripts:registrations.map(

                    r=>r.active ? r.active.scriptURL : null

                )

            };

        }

        """

    )

    return{

        "cookies":cookie_summary,

        "local_storage":local_storage,

        "session_storage":session_storage,

        "indexed_db":indexed_db,

        "cache_api":cache_api,

        "service_worker":service_worker

    }