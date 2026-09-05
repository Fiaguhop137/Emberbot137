#include <iostream>
#include <cstdlib>
#include <unistd.h>
#include <vector>
#include <cstdio>
#include <sys/wait.h>
int main(int argc,char* argv[]){
    if(argc<2){return 1;}
    FILE* pipe=popen("amixer get Master | awk -F'[][]' '/Left:/ {print $2}' | tr -d '%'", "r");
    int volume;
    FILE* pipes=popen("pactl list sink-inputs short | awk '{print $1}'", "r");
    std::vector<int> sink;
    int id;
    while (fscanf(pipes,"%d",&id)==1){sink.push_back(id);}
    pclose(pipes);
    for (int id:sink){static_cast<void>(std::system(("pactl set-sink-input-mute "+std::to_string(id)+" 1").c_str()));}
    int x=fscanf(pipe,"%d",&volume);
    pclose(pipe);
    if(x!=1){return 1;}
    static_cast<void>(std::system("amixer set Master 67% > /dev/null 2>&1"));
    pid_t pid=fork();
    if (pid==0){
        char* args[]={(char*)"flite",(char*)"-voice",(char*)"slt",(char*)"-t",argv[1],nullptr};
        execvp("flite",args);
        perror("execvp");
        _exit(1);
    }else{
        int status;
        if(pid>0){waitpid(pid,&status,0);}
        static_cast<void>(std::system(("amixer set Master "+std::to_string(volume)+"% > /dev/null 2>&1").c_str()));
        for(int id:sink){static_cast<void>(std::system(("pactl set-sink-input-mute "+std::to_string(id)+" 0").c_str()));}
    }
}
