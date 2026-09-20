const firebaseConfig={
    apiKey:"AIzaSyCOYlcW-Y_vLHvRIgD8aKsu6vKIVUGkT20",
    authDomain:"discord-fia.firebaseapp.com",
    databaseURL:"https://discord-fia-default-rtdb.firebaseio.com",
    projectId:"discord-fia",
    storageBucket:"discord-fia.firebasestorage.app",
    messagingSenderId:"169321143262",
    appId:"1:169321143262:web:536821013cfaefe7ea9b4f",
    measurementId:"G-YXNGJPDFMB"
};

const chatbox=document.getElementById("chatbox");
const input=document.getElementById("input");

const ENCRYPTED_BOT_TOKEN=`{"salt": "djrf8nJ4YegFBvpBh2MA4A==", "iv": "VsHCIS1os2XN1dgj", "ciphertext": "uQ2h4h72Y+f0dzqDGOZXhKwXGA/N6ws9M7gdK+J4CRcoDCPBrN9301nOCb1M8YuBoWH5D36K5QEpWeOBzkOLKdH+cFiEAaY6lYm17UACTFKX64x16uHQ3Q=="}`;

let BOT_TOKEN="";
let socket=null;
let heartbeatTimer=null;
let sequence=null;

let firebaseMessages=null;
let firebasePush=null;


function log(message){
    const line=document.createElement("div");

    line.textContent=message;

    chatbox.appendChild(line);
    chatbox.scrollTop=chatbox.scrollHeight;

    console.log(message);
}


async function initializeFirebase(){
    const firebaseAppModule=await import(
        "https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js"
    );

    const firebaseDatabaseModule=await import(
        "https://www.gstatic.com/firebasejs/12.19.0/firebase-database.js"
    );

    const app=firebaseAppModule.initializeApp(firebaseConfig);

    const db=firebaseDatabaseModule.getDatabase(app);

    firebaseMessages=firebaseDatabaseModule.ref(
        db,
        "messages"
    );

    firebasePush=firebaseDatabaseModule.push;

    log("Firebase initialized.");
}


async function sendFirebase(channelId,content){
    try{
        if(!firebaseMessages||!firebasePush){
            log("Firebase is not initialized.");
            return false;
        }

        const message=await firebasePush(
            firebaseMessages,
            {
                type:"message",
                sender:"chromebook",
                channel_id:channelId,
                data:content,
                timestamp:Date.now()
            }
        );

        log(`Firebase message sent: ${message.key}`);

        return true;
    }catch(error){
        console.error("Firebase error:",error);

        log(`Firebase failed: ${error.message}`);

        return false;
    }
}


function sendGateway(op,data){
    if(!socket||socket.readyState!==WebSocket.OPEN){
        log("Gateway is not connected.");
        return;
    }

    socket.send(JSON.stringify({
        op,
        d:data
    }));
}


async function decrypt(encrypted,password){
    const data=JSON.parse(encrypted);

    const salt=Uint8Array.from(
        atob(data.salt),
        c=>c.charCodeAt(0)
    );

    const iv=Uint8Array.from(
        atob(data.iv),
        c=>c.charCodeAt(0)
    );

    const ciphertext=Uint8Array.from(
        atob(data.ciphertext),
        c=>c.charCodeAt(0)
    );

    const passwordBytes=new TextEncoder().encode(password);

    const passwordKey=await crypto.subtle.importKey(
        "raw",
        passwordBytes,
        "PBKDF2",
        false,
        ["deriveKey"]
    );

    const key=await crypto.subtle.deriveKey(
        {
            name:"PBKDF2",
            salt,
            iterations:600000,
            hash:"SHA-256"
        },
        passwordKey,
        {
            name:"AES-GCM",
            length:256
        },
        false,
        ["decrypt"]
    );

    const plaintext=await crypto.subtle.decrypt(
        {
            name:"AES-GCM",
            iv
        },
        key,
        ciphertext
    );

    return new TextDecoder().decode(plaintext);
}


function connect(){
    log("Connecting to Discord...");

    socket=new WebSocket(
        "wss://gateway.discord.gg/?v=10&encoding=json"
    );

    socket.addEventListener("open",()=>{
        log("WebSocket connected.");
    });

    socket.addEventListener("message",event=>{
        let packet;

        try{
            packet=JSON.parse(event.data);
        }catch{
            log("Received invalid Gateway JSON.");
            return;
        }

        console.log("Gateway packet:",packet);

        if(packet.s!==null){
            sequence=packet.s;
        }

        switch(packet.op){

            case 10:{
                const interval=packet.d.heartbeat_interval;

                log(
                    `Heartbeat interval: ${interval}ms.`
                );

                clearInterval(heartbeatTimer);

                heartbeatTimer=setInterval(()=>{
                    sendGateway(1,sequence);
                },interval);

                sendGateway(2,{
                    token:BOT_TOKEN,
                    intents:1|512|32768,
                    properties:{
                        os:"linux",
                        browser:"emberbot137",
                        device:"emberbot137"
                    }
                });

                log("Identify sent.");

                break;
            }

            case 0:{
                if(packet.t==="READY"){
                    log(
                        `Logged in as ${packet.d.user.username}.`
                    );

                    log("Gateway connection ready.");
                }

                if(packet.t==="MESSAGE_CREATE"){
                    if(
                        packet.d.channel_id!=="1532936635682000996"
                    ){
                        log(
                            `${packet.d.author.username}: `+
                            `${packet.d.content}`
                        );
                    }
                }

                if(packet.t==="INTERACTION_CREATE"){
                    const interaction=packet.d;

                    log(
                        "INTERACTION_CREATE received."
                    );

                    if(interaction.data?.name){
                        log(
                            `Command: /${interaction.data.name}`
                        );
                    }

                    respondToInteraction(interaction);
                }

                break;
            }

            case 1:{
                sendGateway(1,sequence);
                break;
            }

            case 7:{
                log("Discord requested reconnect.");

                clearInterval(heartbeatTimer);
                heartbeatTimer=null;

                socket.close();

                break;
            }

            case 9:{
                log(
                    "Discord rejected the Gateway session."
                );

                clearInterval(heartbeatTimer);
                heartbeatTimer=null;

                break;
            }

            case 11:{
                console.log("Heartbeat ACK.");

                break;
            }

            default:{
                console.log(
                    "Unhandled Gateway opcode:",
                    packet.op,
                    packet
                );

                break;
            }
        }
    });

    socket.addEventListener("close",event=>{
        clearInterval(heartbeatTimer);

        heartbeatTimer=null;

        log(
            `Disconnected. Code: ${event.code}`
        );
    });

    socket.addEventListener("error",error=>{
        console.error(
            "WebSocket error:",
            error
        );

        log("WebSocket error.");
    });
}


input.addEventListener("keydown",async event=>{
    if(event.key!=="Enter"){
        return;
    }

    const message=input.value.trim();

    if(!message){
        return;
    }

    input.value="";

    const channelId="1530032067084292097";

    await sendFirebase(
        channelId,
        message
    );
});


async function main(){
    const password=prompt("Password:");

    if(password===null){
        log("Password entry cancelled.");
        return;
    }

    try{
        BOT_TOKEN=await decrypt(
            ENCRYPTED_BOT_TOKEN,
            password
        );

        log("Credentials decrypted.");

        await initializeFirebase();
    }catch(error){
        console.error(
            "Initialization failed:",
            error
        );

        log(
            "Invalid password, Firebase initialization failed, "+
            "or corrupted encrypted data. Reload the page and try again."
        );

        return;
    }

    connect();
}


main();