# ds_project_ws2223
Group members: Sena Tarpan, Peter Hoesch, Yun Ye <br>

### Introduction
![model](img/System%20Architecture.png)
Our goal in this project is to build a fully functioning, distributed system for Auction.
### Requirements<br>
Following additional package will be needed:
1. click
2. secrets
3. tqdm
4. threading
### Running<br>
Run the client with a single command:
```
python Client.py --port5700
```
the default port will be 5700, if there are multiple clients, you should manually change the port.<br>
In order to start the Server, you need to enter two additional parameters
```
python Server.py --port 10001 --opt 1
```
the parameter `port` identify the port Server connected to. (for UDP) <br>
with `opt` you can define whether the Server is the entry point of this system. The default setting in this case will be `port 10001` and `opt 1` <br>
![terminal](img/terminal.jpg) <br>
The command supported currently:
1. report: get the info of server
2. find: broadcasting and turn on udp listening after that
3. server: (server only feature) print the servers group list
4. client: (server only feature) print the clients group list
5. join: send request to the main server to join the group
6. ~~udp_listen: accept request at the udp port~~
7. exit

### Progress<br>
![broadcast](img/broadcast.jpg) <br>
27.11.2022: tune the broadcast function. Gonna watch the Worldcup! `:smiley:`<br>
28.11.2022: multithread tested and added so that the system can handle multi-request.<br>
03.12.2022: realizing the multithread function. Now the model can automatically set up the udp_listen function. Optimize the structure of codes. New abstract function for auction component:`interface()`, `state_update()`
and some small gadgets. Broadcast logic finished! unused user function deleted! Now we have a fully functioning broadcast system!<br>


### TODO<br>
1. ~~broadcast logic~~
2. heartbeat
3. ip mask for broadcast
4. Debug mode
5. comment!!!!
6. make code more beautiful