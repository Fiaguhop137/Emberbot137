const chatbox=document.getElementById("chatbox");
const input=document.getElementById("input");
const ENCRYPTED_BOT_TOKEN=`{"salt": "PWgZHJ51oLx2nYYLOzEDng==", "iv": "Ge/OoP2uC0TDhXp4", "ciphertext": "EPvm3ihdI7GehknAU+JbN3A4O3XH/691WMcaxCVDjz+ZihO3aid0hafS+5Pf7QU90l9yRgLpLCP9iSeaMrJ/euMTjMgYo2fUVohiDLdYF7z15nAaWEv8DQ=="}`;
const ENCRYPTED_WEBHOOK=`{"salt": "aXj9f3BPts1XDoTv27JYnQ==", "iv": "/LJ2tZoxwTwl+KVK", "ciphertext": "fNomx526vBoG/xv3GMuxyytmu5/T5+CUJyJwdOm9YkSLBQAl4hT9PCQJM4Pz5IpmZH9PfGVY+66IupUM30d30nTNgmKSmwluD+r4Uj/U9xyqk7jIYjvOBruPQC+kJ3Nt4I3l/dFzs2ZZW5Mgp6z4A+adU0CRqRJeuoYf2na61bMajMvBOmfW7Mk="}`;
let WEBHOOK_URL="";
let BOT_TOKEN="";
let socket=null;
let heartbeatTimer=null;
let sequence=null;
function log(message){
    const line=document.createElement("div");
    line.textContent=message;
    chatbox.appendChild(line);
    chatbox.scrollTop=chatbox.scrollHeight;
    console.log(message);
}
function sendGateway(op,data){
    if (!socket||socket.readyState!==WebSocket.OPEN) {
        log("Gateway is not connected.");
        return;
    }
    socket.send(JSON.stringify({op,d:data}));
}
async function sendWebhook(content){
    try{
        const response=await fetch(WEBHOOK_URL,{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify({content:content})
        });
        if(!response.ok){
            const body=await response.text();
            log(`Webhook failed: ${response.status} ${body}`);
            return false;
        }
        return true;
    }catch(error){
        console.error("Webhook error:",error);
        log(`Webhook failed: ${error.message}`);
        return false;
    }
}
async function decrypt(encrypted,password){
    const data=JSON.parse(encrypted);
    const salt=Uint8Array.from(atob(data.salt),c=>c.charCodeAt(0));
    const iv=Uint8Array.from(atob(data.iv),c=>c.charCodeAt(0));
    const ciphertext=Uint8Array.from(atob(data.ciphertext),c=>c.charCodeAt(0));
    const passwordBytes=new TextEncoder().encode(password);
    const passwordKey=await crypto.subtle.importKey("raw",passwordBytes,"PBKDF2",false,["deriveKey"]);
    const key=await crypto.subtle.deriveKey({name:"PBKDF2",salt,iterations:600000,hash:"SHA-256"},passwordKey,{name:"AES-GCM",length: 256},false,["decrypt"]);
    const plaintext=await crypto.subtle.decrypt({name: "AES-GCM",iv},key,ciphertext);
    return new TextDecoder().decode(plaintext);
}
function connect(){
    log("Connecting to Discord...");
    socket=new WebSocket("wss://gateway.discord.gg/?v=10&encoding=json");
    socket.addEventListener("open",()=>{log("WebSocket connected.");});
    socket.addEventListener("message",event=>{
        let packet;
        try{
            packet=JSON.parse(event.data);
        }catch{
            log("Received invalid Gateway JSON.");
            return;
        }
        console.log("Gateway packet:", packet);
        if (packet.s !== null) {
            sequence=packet.s;
        }
        switch (packet.op) {
            case 10: {
                const interval=packet.d.heartbeat_interval;
                log(`Heartbeat interval: ${interval}ms.`);
                clearInterval(heartbeatTimer);
                heartbeatTimer=setInterval(()=>{sendGateway(1,sequence);},interval);
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
                if (packet.t==="READY") {
                    log(`Logged in as ${packet.d.user.username}.`);
                    log("Gateway connection ready.");
                }
                if(packet.t==="MESSAGE_CREATE"){
                    if(packet.d.channel_id!=="1532936635682000996"){
                        log(`${packet.d.author.username}: `+`${packet.d.content}`);
                    }
                }
                if(packet.t==="INTERACTION_CREATE"){
                    const interaction=packet.d;
                    log("INTERACTION_CREATE received.");
                    if (interaction.data?.name){log(`Command: /${interaction.data.name}`);}
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
                log("Discord rejected the Gateway session.");
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
    socket.addEventListener("close",event => {
        clearInterval(heartbeatTimer);
        heartbeatTimer=null;
        log(`Disconnected. Code: ${event.code}`);
    });
    socket.addEventListener("error",error =>{
        console.error("WebSocket error:",error);
        log("WebSocket error.");
    });
}
input.addEventListener("keydown",async event=>{
    if(event.key !== "Enter"){return;}
    const message=input.value.trim();
    if(!message){return;}
    input.value="";
    const channelId="1530032067084292097";
    await sendWebhook(channelId+`|`+message);
});
async function main(){
    const password=prompt("Password:");
    if(password===null){
        log("Password entry cancelled.");
        return;
    }
    try{
        WEBHOOK_URL=await decrypt(ENCRYPTED_WEBHOOK,password);
        BOT_TOKEN=await decrypt(ENCRYPTED_BOT_TOKEN,password);
    }catch(error){
        console.error("Decryption failed:",error);
        log("Invalid password or corrupted encrypted data. Reload the page and try again.");
        return;
    }
    log("Credentials decrypted.");
    connect();
}
main();