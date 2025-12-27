// Dom elements declaration
import * as API from "./apiCall.js";
// console.log('API object at runtime:', API);
const barOfButtons = document.querySelector('#butonBar');
const brandHub = document.querySelector('#brandHub');
const brandAdderBtn = document.querySelector('#markaEkleyenButon');
const brandAdderwJSONBtn = document.querySelector('#markaJSONlaEkleyenButon');
const brandAdderwJSONInp = document.querySelector('#markaEkleJsonInp');

function deasciifierNLowerer(str) {
    const charMap = {
        'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'İ': 'i', 'Ö': 'o', 'Ç': 'c', 'ı': 'i',
        'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'
    };

    return str
        .replace(/[\u00C0-\u017F]/g, ch => charMap[ch] || ch)
        .replace(/\s+/g, '') // remove all spaces (and tabs, newlines)
        .toLowerCase();
}


function brandObjectifier() {
    let brandNameInp = document.querySelector('input[name="markaAdiGirdi"]');
    let brandLangs = document.querySelector('input[name="dillerInp"]').value.split(",")
    // alert(brandLangs[1])

    let brandObject = {
        "name": brandNameInp.value,
        "langs": []
    }

    brandLangs.forEach(element => {
        brandObject.langs.push(element);
    });
    addBrand(JSON.stringify(brandObject))
}

function brandJson() {
    const file = brandAdderwJSONInp.files[0];

    if (!file) {
        console.error("No file selected.");
        return;
    }

    const reader = new FileReader();

    reader.onload = function (e) {
        try {
            const brandData = JSON.parse(e.target.result);

            for (const brandKey in brandData) {
                if (brandData.hasOwnProperty(brandKey)) {
                    const brand = brandData[brandKey];

                    // Optional structure validation
                    if (
                        typeof brand.name !== "string" ||
                        !Array.isArray(brand.langs)
                    ) {
                        console.warn(`Skipping invalid brand entry: ${brandKey}`);
                        continue;
                    }

                    // Convert brand to JSON string and pass to addBrand
                    addBrand(JSON.stringify(brand));
                }
            }

        } catch (err) {
            console.error("Error parsing JSON file:", err);
        }
    };

    reader.onerror = function () {
        console.error("Error reading file:", reader.error);
    };

    reader.readAsText(file);
}

function getPrompts(brand) {
    let systemBox = document.querySelector(`#${brand}prompts .system.promptBox textarea`)
    let subtitleBox = document.querySelector(`#${brand}prompts .subtitle.promptBox textarea`)
    let contentBox = document.querySelector(`#${brand}prompts .content.promptBox textarea`)
    let metaDescBox = document.querySelector(`#${brand}prompts .system.promptBox textarea`)
    return {
        "system": `${systemBox.value}`,
        "subtitle": `${subtitleBox.value}`,
        "content": `${contentBox.value}`,
        "metaDesc": `${metaDescBox.value}`,
    }
}




function addBrand(brandObj) {
    let brandObject = JSON.parse(brandObj);
    let brandNameDeasciified = deasciifierNLowerer(brandObject.name);

    let brandBtn = document.createElement('button');
    brandBtn.classList.add('tablink');
    brandBtn.addEventListener('click', () => openPage(brandNameDeasciified));
    brandBtn.innerText = `${brandObject.name}`;
    barOfButtons.append(brandBtn)


    let brandBodyLangs = '';
    brandObject.langs.forEach(element => {
        brandBodyLangs += `<div id="${brandNameDeasciified}${deasciifierNLowerer(element)}">
            <h3>${element}</h3>
            <div>
                <label>İçerik(HTML)</label>
                <div class="contentBox"></div>
                <button class="copyBtn" data-box="contentBox">Copy</button><br/>
                <label>Meta Desc</label>
                <div class="metaDescBox"></div>
                <button class="copyBtn" data-box="metaDescBox">Copy</button><br/>
                <label>Meta Keywords</label>
                <div class="metaKwBox" class="metaKwBox"></div>
                <button class="copyBtn" data-box="metaKwBox">Copy</button><br/>
            </div>
        </div>`
    });

    let brandBody = `<div id="${brandNameDeasciified}" class="tabcontent">
        <h2>${brandObject.name}</h2>
        <label>Username: </label><input id="${brandNameDeasciified}UsernameInp"><br/>
        <label>Password: </label><input id="${brandNameDeasciified}PasswordInp"><br/>
        <label>Login: </label><button id="${brandNameDeasciified}LoginBtn">Login</button><br/><br/><br/>
        <label>Başlık</label>
        <input type="text" id="${brandNameDeasciified}BaslikInp"><br>
        <button class="sendAI" marka="${brandNameDeasciified}" id="${brandNameDeasciified}SendAI">AI'a Gönder</button><br>
        <p id="${brandNameDeasciified}onGoingProcess">Waiting</p>
        ${brandBodyLangs}
        <div id="${brandNameDeasciified}prompts">
            <div class="system promptBox"><h4>System Prompt</h4><br/><textarea spellcheck="false">${brandObject.PROMPTS.system}</textarea></div>
            <div class="subtitle promptBox"><h4>Subtitle Prompt</h4><br/><textarea spellcheck="false">${brandObject.PROMPTS.subtitle}</textarea></div>
            <div class="content promptBox"><h4>Content Prompt</h4><br/><textarea spellcheck="false">${brandObject.PROMPTS.content}</textarea></div>
            <div class="metaDesc promptBox"><h4>MetaDesc Prompt</h4><br/><textarea spellcheck="false">${brandObject.PROMPTS.metaDesc}</textarea></div>
        </div>
        <div id="${brandNameDeasciified}History">
            <h3>History</h3>
        </div>
        </div>`


    brandHub.insertAdjacentHTML('beforeend', brandBody)
    API.attachUploadListener(brandNameDeasciified, brandObject.postParameters)

    const loginBtn = document.getElementById(`${brandNameDeasciified}LoginBtn`);
    if (loginBtn) {
        if (!brandObject.url) {
            loginBtn.disabled = true;
            loginBtn.textContent = 'No CMS Setup';
            loginBtn.title = 'This brand skips auto-uploads—handle manual.';
            console.log(`Skipped login for ${brandNameDeasciified}: No Vayes URL.`);
        } else {
            loginBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                const result = await API.loginToPanel(brandNameDeasciified, brandObject.url);
                if (result.success) {
                    loginBtn.textContent = 'Logged In!';
                    loginBtn.style.backgroundColor = 'green';
                } else {
                    alert(`Login flop: ${result.error}`);
                    loginBtn.style.backgroundColor = 'red';
                }
            });
        }
    } else {
        console.error(`Login btn MIA for ${brandNameDeasciified}—check ID.`);
    }

    brandHub.addEventListener('click', (e) => {
        if (e.target.classList.contains('copyBtn')) {
            const box = e.target.previousElementSibling;  // Grabs the <div class="...Box">
            if (box && box.textContent) {
                navigator.clipboard.writeText(box.textContent.trim()).then(() => {
                    // Quick UX: Flash "Copied!" on button for 1s
                    const btn = e.target;
                    const origText = btn.textContent;
                    btn.textContent = 'Copied!';
                    btn.style.background = '#4CAF50';
                    setTimeout(() => {
                        btn.textContent = origText;
                        btn.style.background = '';  // Reset
                    }, 1000);
                }).catch(err => console.error('Clipboard fail:', err));  // User denied perms?
            }
        }
    });

    // console.log("Post parameters",JSON.stringify(brandObject.postParameters))

    let sendAIBtn = document.getElementById(`${brandNameDeasciified}SendAI`);
    sendAIBtn.addEventListener('click', () => API.generate(brandObject.name, brandObject.langs, undefined, brandObject.services, brandObject.audience, brandObject.description, brandObject.keywords, getPrompts(brandNameDeasciified), brandObject.postParameters));
}

// EventListeners



brandAdderBtn.addEventListener('click', brandObjectifier);
brandAdderwJSONBtn.addEventListener('click', brandJson);
