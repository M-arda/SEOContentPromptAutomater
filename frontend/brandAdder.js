// Dom elements declaration
import * as API from "./apiCall.js";
const barOfButtons = document.querySelector('#butonBar');
const tabHub = document.querySelector('#brandHub');
const brandAdderBtn = document.querySelector('#markaEkleyenButon');
const brandAdderwJSONBtn = document.querySelector('#markaJSONlaEkleyenButon');
const brandAdderwJSONInp = document.querySelector('#markaEkleJsonInp');


function deasciifierNLowerer(str) {
    const charMap = {
        'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'İ': 'i', 'Ö': 'o', 'Ç': 'c', 'ı': 'i',
        'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'
    };

    return str.replace(/[\u00C0-\u017F]/g, function (ch) {
        return charMap[ch] || ch;
    }).toLowerCase();
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
                <label>Meta Desc</label>
                <div class="metaDescBox"></div>
            </div>
        </div>`
    });

    let brandBody = `<div id="${brandNameDeasciified}" class="tabcontent">
        <h2>${brandObject.name}</h2>
        <label>Başlık</label>
        <input type="text" id="${brandNameDeasciified}BaslikInp"><br>
        <button class="sendAI" marka="${brandNameDeasciified}" id="${brandNameDeasciified}SendAI">AI'a Gönder</button><br>
        <p id="${brandNameDeasciified}onGoingProcess"></p>${brandBodyLangs}</div>`

    tabHub.insertAdjacentHTML('beforeend', brandBody)

    let sendAIBtn = document.getElementById(`${brandNameDeasciified}SendAI`);
    sendAIBtn.addEventListener('click', () => API.generate(brandNameDeasciified));
}

// EventListeners



brandAdderBtn.addEventListener('click', brandObjectifier);
brandAdderwJSONBtn.addEventListener('click', brandJson);
