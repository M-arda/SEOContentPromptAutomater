


function deasciifierNLowerer(str) {
    const charMap = {
        'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'İ': 'i', 'Ö': 'o', 'Ç': 'c', 'ı': 'i',
        'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'
    };

    return str
        .replace(/[\u00C0-\u017F]/g, ch => charMap[ch] || ch)
        .replace(/\s+/g, '')
        .toLowerCase();
}

// let soundFiles = [];

// async function loadSounds() {
//     if (soundFiles.length > 0) return;
//     try {
//         const res = await fetch('/sounds');
//         if (!res.ok) throw new Error('List fetch flop');
//         const data = await res.json();
//         soundFiles = data.sounds;
//         console.log(`Loaded ${soundFiles.length} sounds`);
//     } catch (e) {
//         console.error('Sounds load died:', e);
//         soundFiles = [];
//     }
// }

// let audioCtx;

// function playSound() {
//     if (!audioCtx) {
//         audioCtx = new (window.AudioContext || window.webkitAudioContext)();
//     }

//     if (soundFiles.length === 0) {
//         console.log("No sounds? Skipping ding.");
//         return;
//     }

//     const randomSound = soundFiles[Math.floor(Math.random() * soundFiles.length)];

//     fetch(`/sounds/${randomSound}`)
//         .then(res => res.arrayBuffer())
//         .then(buf => audioCtx.decodeAudioData(buf))
//         .then(decoded => {
//             const src = audioCtx.createBufferSource();
//             const gain = audioCtx.createGain();
//             gain.gain.value = 0.5;

//             src.buffer = decoded;
//             src.connect(gain);
//             gain.connect(audioCtx.destination);
//             src.start();
//         })
//         .catch(e => console.log("Audio load/play issue:", e));
// }



export async function restore_from_jobId(job_Id) {
    try {
        const progRes = await fetch(`http://localhost:3169/progress/${job_Id}`);
        console.log('Progress fetch status:', progRes.status);  // 200 or bust?
        if (!progRes.ok) throw new Error(`Progress fetch: ${progRes.status}`);
        const progData = await progRes.json();
        console.log('Progress data:', progData);  // Full guts

        if (progData.status === 'done' && progData.data) {
            // Populate from final data
            const data = progData.data;
            let contents = data.contents;
            let metaDescs = data.metaDescs;
            let metaKwords = data.metaKeywords;
            let subTitles = data.subtitles;
            let langs = data.langs;

            let restore_body = "";

            langs.forEach(lang => {
                restore_body += `
                    <div>
                        <h5>${lang}</h5>
                        <label>Content:</label><textarea>${contents[lang]}</textarea><br/>
                        <label>MetaDescs:</label><textarea>${contents[lang]}</textarea><br/>
                        <label>MetaKwords:</label><textarea>${contents[lang]}</textarea><br/>
                    </div>
                `
            });

            let restore = `<div>
                ${restore_body}
            </div>`

            document.querySelector('#Home').insertAdjacentHTML('beforeend',restore)

        } else if (progData.status === 'error') {
            console.log("Something went wrong",progData.message)

            // playSound()
        }
    } catch (err) {
        console.error('Poll bombed:', err);
        clearInterval(pollInterval);
        processEl.textContent = 'Poll connection issue—retry?';
    }
}



export async function generate(brand, langs, model, service, audience, description, brandKeywords, prompts, postParameters) {
    model = "deepseek-v3.1:671b-cloud"
    const brandDeasciified = deasciifierNLowerer(brand);
    const processEl = document.getElementById(`${brandDeasciified}onGoingProcess`);  // Grab for updates
    if (!processEl) {
        console.error(`No process el for ${brandDeasciified}`);
        return;
    }
    processEl.textContent = 'Starting...';  // Kickoff vibe

    const Inptopic = document.querySelector(`#${brandDeasciified}BaslikInp`).value;

    // Map content boxes for each language
    const historyBox = document.querySelector(`#${brandDeasciified}History`)
    const contentBoxMap = {};
    const metaDescBoxMap = {};
    const metaKwsBoxMap = {};
    langs.forEach(lang => {
        const langDeasciified = deasciifierNLowerer(lang);  // Deasciify lang for ID match
        const contentBox = document.querySelector(`#${brandDeasciified}${langDeasciified} .contentBox`);
        const metaDescBox = document.querySelector(`#${brandDeasciified}${langDeasciified} .metaDescBox`);
        const metaKwsBox = document.querySelector(`#${brandDeasciified}${langDeasciified} .metaKwBox`);
        if (contentBox) {
            contentBoxMap[lang] = contentBox;
        }
        if (metaDescBox) {
            metaDescBoxMap[lang] = metaDescBox;
        }
        if (metaKwsBox) {
            metaKwsBoxMap[lang] = metaKwsBox;
        }
    });

    const res = await fetch("http://localhost:3169/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            brand: brand,
            topic: Inptopic,
            services: service,
            audience: audience,
            description: description,
            brandKeywords: brandKeywords,
            ai_model: model,
            langs: langs,
            prompts: prompts
        })
    });

    console.log('Generate fetch done, status:', res.status);

    if (!res.ok) {
        const errBody = await res.text();
        console.error(`API start bombed: ${res.status} ${res.statusText} - Body: ${errBody}`);
        processEl.textContent = `Start failed: ${res.status} - ${res.statusText}`;
        return;
    }

    const startData = await res.json();
    console.log('Full startData:', startData);
    console.log('Job_id extracted:', startData.job_id);
    const jobId = startData.job_id;
    if (!jobId) {
        console.error('No job_id from backend—progress dead.');
        processEl.textContent = 'No job started—retry?';
        return;
    }
    console.log(`Job kicked: ${jobId}`);

    let pollInterval;


    async function pollProgress() {
        console.log('Poll attempt starting for:', jobId);  // Does this fire?
        try {
            const progRes = await fetch(`http://localhost:3169/progress/${jobId}`);
            console.log('Progress fetch status:', progRes.status);  // 200 or bust?
            if (!progRes.ok) throw new Error(`Progress fetch: ${progRes.status}`);
            const progData = await progRes.json();
            console.log('Progress data:', progData);  // Full guts

            processEl.textContent = `${progData.step || 0}: ${progData.message}`;
            processEl.style.color = progData.status === 'done' ? 'green' : progData.status === 'error' ? 'red' : 'orange';

            if (progData.status === 'done' && progData.data) {
                clearInterval(pollInterval);
                processEl.textContent = 'Done';
                // Populate from final data
                const data = progData.data;
                let contents = data.contents;
                let metaDescs = data.metaDescs;
                let metaKwords = data.metaKeywords;
                let subTitles = data.subtitles;

                Object.keys(contents || {}).forEach(langsContent => {
                    if (contentBoxMap[langsContent]) {
                        contentBoxMap[langsContent].textContent = contents[langsContent];
                    }
                });

                Object.keys(metaDescs || {}).forEach(langsDesc => {
                    if (metaDescBoxMap[langsDesc]) {
                        metaDescBoxMap[langsDesc].textContent = metaDescs[langsDesc];
                    }
                });

                Object.keys(metaKwords || {}).forEach(langsKws => {
                    if (metaKwsBoxMap[langsKws]) {
                        metaKwsBoxMap[langsKws].textContent = metaKwords[langsKws];
                    }
                });

                let historyLangs = ``;
                data.langs.forEach(element => {
                    historyLangs += `
                        <h3>${data.topics[element]}</h3>
                        <h4>${element}</h4>
                        <label>Content: </label>
                        <textarea oninput="updateLabel(this)">${contents[element]}</textarea><br/>
                        <label>MetaDesc: </label>
                        <textarea oninput="updateLabel(this)">${metaDescs[element]}</textarea><br/>
                        <label>Keywords :</label>
                        <textarea oninput="updateLabel(this)">${metaKwords[element]}</textarea><br/>
                    `
                })

                let historyHTML = `
                    <div class="historyElement">
                        <label>Be careful with article ID you might wipe off another article keep it 0 unless you know what you are doing:&nbsp;&nbsp;</label>
                        <input class="articleId" type="number" value="0" disabled><br/>
                        <button id="${brandDeasciified}upload">Add to panel</button><br/>
                        <label>${jobId}</label><br/>
                        <div>${historyLangs}</div>
                    </div>
                `

                // historyHTML = historyHTML.replace('<div class="historyElement">', `<div class="historyElement" data-post-params='${JSON.stringify(postParameters)}'>`);
                historyBox.insertAdjacentHTML('beforeend', historyHTML)

                // console.log('Subtitles:', subTitles); 

                // playSound()

            } else if (progData.status === 'error') {
                clearInterval(pollInterval);
                processEl.textContent = `Error: ${progData.message}`;

                // playSound()
            }
        } catch (err) {
            console.error('Poll bombed:', err);
            clearInterval(pollInterval);
            processEl.textContent = 'Poll connection issue—retry?';
        }
    };

    console.log('Interval armed, first poll kicking now');
    pollInterval = setInterval(pollProgress, 1000);
    pollProgress();
}



// Call once per-brand in initializer: attachUploadListener(brandNameDeasciified);
export function attachUploadListener(brandDeasciified, postParameters) {
    const historyBox = document.querySelector(`#${brandDeasciified}History`);
    if (!historyBox) {
        console.error(`History box for ${brandDeasciified} ghosted—listener skipped.`);
        return;
    }

    historyBox.addEventListener('click', (e) => {
        if (!e.target.matches('[id$="upload"]')) return;

        const button = e.target;
        const historyEl = button.closest('.historyElement');
        if (!historyEl) return console.error('HistoryEl AWOL—upload bailed.');

        button.disabled = true;
        button.textContent = 'Uploading...';

        handleUpload(brandDeasciified, historyEl, button, postParameters).catch(err => {
            console.error('Handler bombed:', err);
            button.textContent = 'Failed—Try Again?';
            button.style.backgroundColor = 'red';
            button.disabled = false;
        });
    });

    console.log(`Upload listener armed for ${brandDeasciified} history.`);
}


function temizleObj(obj) {
    if (typeof obj === 'string') {
        let cleaned = obj.replace(/\n/g, ' ');

        cleaned = obj.replace(/\s+/g, ' ');

        cleaned = obj.replace(/\\/g, ' ');

        return cleaned.trim();
    }

    if (Array.isArray(obj)) {
        return obj.map(temizleObj)
    }

    if (obj && typeof obj === 'object') {
        const yeniObj = {};
        for (const key in obj) {
            yeniObj[key] = temizleObj(obj[key])
        }

        return yeniObj
    }

    return obj
}


export async function handleUpload(brandDeasciified, historyEl, button, postParameters) {
    try {
        console.log('Static postParams loaded:', postParameters);

        const langSections = historyEl.querySelectorAll('div h4');
        const langMap = {
            'turkish': 'tr', 'english': 'en', 'arabic': 'ar', 'russian': 'ru',
            'french': 'fr', 'spanish': 'es', 'german': 'de', 'italian': 'it',
            'polish': 'pl', 'portuguese': 'pt'
        };

        let titles = {};

        langSections.forEach(e => {
            let langsTitle = e.previousElementSibling.textContent
            titles[langMap[e.textContent.toLowerCase()]] = langsTitle
        })

        langSections.forEach(h4 => {
            const langTitle = h4.previousElementSibling;
            // if (!langTitle && !langTitle.tagName.toLowerCase() === 'h3') {
            //     console.warn(`Skipping h4 after h3 for lang section—topic header?`);
            //     return;  // Bail on this h4 if prev is h3
            // }

            const fullLang = h4.textContent.trim().toLowerCase();
            const isoLang = langMap[fullLang];
            if (!isoLang) return console.warn(`Unknown lang "${fullLang}"—skipping.`);

            let tAs = [];
            let sibling = h4.nextElementSibling;
            while (tAs.length < 3 && sibling) {
                if (sibling.tagName.toLowerCase() === 'textarea') {
                    tAs.push(sibling.value || '');
                }
                sibling = sibling.nextElementSibling;
            }

            if (tAs.length < 3) return console.warn(`Only ${tAs.length} textareas for ${fullLang}—structure off?`);

            // Fix: Grab textContent from langTitle (h3 text as title), deascii/slug it for url
            const titleText = langTitle ? langTitle.textContent.trim() : '';
            postParameters[`title[${isoLang}]`] = titleText;
            postParameters[`url[${isoLang}]`] = `change-this-part-${Math.random()}`.replace(/[\.\s]/, '-');

            postParameters[`content[${isoLang}]`] = tAs[0];
            postParameters[`meta_description[${isoLang}]`] = tAs[1];
            postParameters[`meta_keywords[${isoLang}]`] = tAs[2];
            console.log(`Slurped ${isoLang}: title="${titleText.substring(0, 50)}...", content=${tAs[0].substring(0, 50)}...`);
        });

        // Now send it—POST {brand, postParameters} as JSON body
        if (Object.keys(postParameters).length === 0) throw new Error('Empty postParameters—nothing to upload.');

        const payload = {
            brand: brandDeasciified,
            postParameters  // Backend unpacks this dict
        };

        let cleanedPayload = temizleObj(payload)

        console.log('Full payload pre-send:', payload);

        const uploadRes = await fetch('/upload', {  // Or full localhost:3169 if cross-origin
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cleanedPayload)
        });

        if (!uploadRes.ok) {
            const errBody = await uploadRes.text();
            throw new Error(`Upload crapped: ${uploadRes.status} - ${errBody}`);
        }

        const uploadData = await uploadRes.json();
        console.log('Upload locked in:', uploadData);
        button.textContent = 'Uploaded!';
        button.style.backgroundColor = 'green';

    } catch (err) {
        console.error('Upload derailed:', err);
        button.textContent = 'Failed—Try Again?';
        button.style.backgroundColor = 'red';
    } finally {
        button.disabled = false;
    }
}

export async function loginToPanel(brand, url) {
    const loginBtn = document.querySelector(`#${brand}LoginBtn`);
    const usernameInp = document.querySelector(`#${brand}UsernameInp`);
    const passwordInp = document.querySelector(`#${brand}PasswordInp`);

    if (!loginBtn || !usernameInp || !passwordInp) {
        console.error(`Inputs MIA for ${brand}—check IDs.`);
        return { success: false, error: 'UI elements missing' };
    }

    const username = usernameInp.value.trim();
    const password = passwordInp.value.trim();

    if (!username || !password) {
        console.warn('Empty creds—skipping POST.');
        return { success: false, error: 'Username/password required' };
    }

    // Quick UI lock
    const originalText = loginBtn.textContent;
    loginBtn.disabled = true;
    loginBtn.textContent = 'Logging in...';

    try {
        const loginRes = await fetch("http://localhost:3169/login_to_panel", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                brand: brand,
                url: url,
                username: username,
                password: password
            })
        });

        const loginData = await loginRes.json();
        console.log(loginData)

        if (loginRes.ok && loginData.status === 'logged in') {
            console.log(`Login nailed for ${brand}:`, loginData);
            loginBtn.textContent = 'Logged!';  // Or hide/re-enable for re-try
            loginBtn.style.backgroundColor = 'green';
            return { success: true, data: loginData };
        } else {
            const errorMsg = loginData.error || `Server said no: ${loginRes.status}`;
            console.error(`Login flopped for ${brand}:`, errorMsg);
            alert(`Login failed: ${errorMsg}`);
            return { success: false, error: errorMsg };
        }
    } catch (err) {
        console.error(`Network/login bomb for ${brand}:`, err);
        alert('Connection issue—check localhost:3169?');
        return { success: false, error: err.message };
    } finally {
        loginBtn.disabled = false;
        // loginBtn.textContent = originalText;
        loginBtn.style.backgroundColor = '';
    }
}