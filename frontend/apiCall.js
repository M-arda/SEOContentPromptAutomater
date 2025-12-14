


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

export async function generate(brand, langs, model,service, audience, description,brandKeywords, prompts) {
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
    const historyBox = document.querySelector(`#${brandDeasciified}history`)
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
            prompts:prompts
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
                        <h4>${element}</h4>
                        <label>Content</label>
                        <textarea>${contents[element]}</textarea><br/>
                        <label>MetaDesc</label>
                        <textarea>${metaDescs[element]}</textarea><br/>
                        <label>Keywords</label>
                        <textarea>${metaKwords[element]}</textarea><br/>
                    `
                })

                let historyHTML = `
                    <div class="historyElement">
                        <label>${jobId}</label><br/>
                        <h3>${data.topic}</h3>
                        <div>${historyLangs}</div>
                    </div>
                `


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