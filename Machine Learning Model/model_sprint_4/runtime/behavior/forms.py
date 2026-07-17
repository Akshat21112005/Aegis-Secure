from urllib.parse import urlparse


async def collect_forms(page):

    await page.wait_for_load_state("domcontentloaded")

    await page.wait_for_timeout(2000)

    forms = await page.evaluate(

        """

        () => {

            const result = [];

            const currentDomain = window.location.hostname;

            document.querySelectorAll("form").forEach(form=>{

                const action = form.getAttribute("action") || "";

                let external = false;

                let javascriptAction = false;

                let emptyAction = false;

                let domain = "";

                if(action===""){

                    emptyAction = true;

                }

                if(action.startsWith("javascript:")){

                    javascriptAction = true;

                }

                try{

                    if(action!=="" && !javascriptAction){

                        const url = new URL(action,window.location.href);

                        domain = url.hostname;

                        external = url.hostname!==currentDomain;

                    }

                }

                catch(e){}

                result.push({

                    action:action,

                    action_domain:domain,

                    external_action:external,

                    javascript_action:javascriptAction,

                    empty_action:emptyAction,

                    method:(form.method || "GET").toUpperCase(),

                    enctype:form.enctype,

                    target:form.target,

                    autocomplete:form.autocomplete,

                    novalidate:form.noValidate,

                    input_count:form.querySelectorAll("input").length,

                    password_fields:form.querySelectorAll("input[type=password]").length,

                    email_fields:form.querySelectorAll("input[type=email]").length,

                    hidden_inputs:form.querySelectorAll("input[type=hidden]").length,

                    telephone_fields:form.querySelectorAll("input[type=tel]").length,

                    number_fields:form.querySelectorAll("input[type=number]").length,

                    file_inputs:form.querySelectorAll("input[type=file]").length,

                    checkbox_fields:form.querySelectorAll("input[type=checkbox]").length,

                    radio_fields:form.querySelectorAll("input[type=radio]").length,

                    submit_buttons:form.querySelectorAll("input[type=submit],button[type=submit]").length,

                    required_inputs:form.querySelectorAll("[required]").length,

                    textarea_count:form.querySelectorAll("textarea").length,

                    select_count:form.querySelectorAll("select").length

                });

            });

            return result;

        }

        """

    )

    summary = {

        "form_count":len(forms),

        "external_actions":0,

        "javascript_actions":0,

        "empty_actions":0,

        "post_forms":0,

        "get_forms":0,

        "multipart_forms":0,

        "password_fields":0,

        "email_fields":0,

        "hidden_inputs":0,

        "telephone_fields":0,

        "number_fields":0,

        "file_inputs":0,

        "checkbox_fields":0,

        "radio_fields":0,

        "submit_buttons":0,

        "required_inputs":0,

        "textarea_count":0,

        "select_count":0

    }

    for form in forms:

        if form["external_action"]:

            summary["external_actions"] += 1

        if form["javascript_action"]:

            summary["javascript_actions"] += 1

        if form["empty_action"]:

            summary["empty_actions"] += 1

        if form["method"] == "POST":

            summary["post_forms"] += 1

        else:

            summary["get_forms"] += 1

        if "multipart/form-data" in form["enctype"]:

            summary["multipart_forms"] += 1

        summary["password_fields"] += form["password_fields"]

        summary["email_fields"] += form["email_fields"]

        summary["hidden_inputs"] += form["hidden_inputs"]

        summary["telephone_fields"] += form["telephone_fields"]

        summary["number_fields"] += form["number_fields"]

        summary["file_inputs"] += form["file_inputs"]

        summary["checkbox_fields"] += form["checkbox_fields"]

        summary["radio_fields"] += form["radio_fields"]

        summary["submit_buttons"] += form["submit_buttons"]

        summary["required_inputs"] += form["required_inputs"]

        summary["textarea_count"] += form["textarea_count"]

        summary["select_count"] += form["select_count"]

    return {

        "forms":forms,

        "summary":summary

    }