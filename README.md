# ds_project_ws2223
👋Group members: Sena Tarpan, Peter Hoesch, Yun Ye <br>

### Introduction
<img src="img/mems.jpg" width="300" height="300"><br>
Our goal in this project is to build a fully functioning, distributed system for Auction.The system will be implemented as a many servers-many clients design. The servers are the seller who functions as the main server as well as supplemental servers that provide fault tolerance and scalability. The clients on the other hand works like a thin client machine that provide merely an interface with a very restricted logic and data functionality. The supplemental servers exist to take bids, aggregate them and transfer that data to the main server. For this purpose, each server will be connected to a number of clients. 
### Requirements & Install<br>
Some additional packages might be needed in this project. Runn the following command to install the requirements:<br>
```
pip install -r requirements.txt
```

For the Windows user: It may be a problem with `curses` package.
```
pip install windows-curses
```
### Running<br>
Run the client with a single command:
```
cd Code
python Client.py --port 5700
```
the default port will be 5700, if there are multiple clients, you should manually change the port. <b>Attention: because a single process will use 4 ports, make sure that leave some space between two processes.</b><br>
In order to start the Server, you need to enter two additional parameters
```
cd Code
python Server.py --port 10001 --opt 1
```
the parameter `port` identify the port Server connected to. (for UDP) <br>
with `opt` you can define whether the Server is the entry point of this system. (in the latest update 01.02, the system can run also without specify the main server, the `opt` might be removed in the next version)The default setting in this case will be `port 10001` and `opt 1` <br><br>
<b>For windows Users:</b> In the Code dir you can find a `start_win.bat` file, by clicking on it or using the following command in cmd you'll get 4 terminal windows with 2 servers and 2 clients running. It is useful for do some testing. It includes some common cases, for example 2-client-2-server situation and so on.
```
cd Code/start_up
2_client_2_server.bat
```
<b>The command supported currently:</b>
![terminal](img/broadcast.png) <br>
| Nr. | Command | Description |
| --- | --------------- | ----------------------------------------- |
| 1 | report    | get the info of server |
| 2 | find      | broadcasting and turn on udp listening after that (Now will be done automatically) |
| 3 | server    | (server only feature) print the servers group list |
| 4 | client    | (server only feature) print the clients group list |
| 5 | leave     | clear the memory, ps: for main server is to cancel the priority |
| 6 | clear     | clear screen to make the terminal more clean. |
| 7 | queue     | To show the elements in the hold-back-queue. |
| 8 | multi1(or 2)| for the multicast testing. <b>multi1</b> will send out 4 messages with sequence number 1 to 4 with 10 seconds latency before the second message. <b>multi2</b> will send out a single udp message with sequence number 5. In the test, the multi1 should be executed on one server and right after that multi2 on another. |
| 9 | intercept   | Blocking the next incoming request with sequence number greater than 0 |
| 10 | block      | Block the election to perform ring failure test |
| 11 | history    | To check the bit history |
| 12 | bit        | (client only feature) to raise the bit in format `bit <Price>` |
| 13 | yy-        | the command start with yy(yyserver, yy client, yyreport and yyhistory) to execute command in the whole group |
| 14 | exit       | exit the programm |

<br>
Look in the programm for more details!<br>

Each time you run the code, a login file will be created in the log directory with the name of the specified port, like `5700_debug.log`, which help you to do the debugging and further development.
<details>
  <summary>
    logging example
  </summary>
INFO:root:SERVER activate on<br>
ID: 			e2e36f28-0c6a-491f-bfc1-e68c744d928b<br>
Address: 		192.168.0.200:10000 <br>
Broadcast: 		192.168.0.255:5972<br>
Main Server: 		('192.168.0.200', 10000)<br>
Is_Main: 		True<br>
Number of Clients: 	0<br>
Sequence number: 	1<br>
INFO:root:{'ID': 'af5bc12a-cca3-4856-a050-1f8480382548', 'METHOD': 'DISCOVERY', 'SEQUENCE': 0, 'CONTENT': {'TYPE': 'CLIENT', 'UDP_ADDRESS': ('192.168.0.200', 5710)}, 'SENDER_ADDRESS': ('192.168.0.200', 62287)}<br>
DEBUG:root:User input: report<br>
DEBUG:root:User input: start<br>
INFO:root:{'ID': 'af5bc12a-cca3-4856-a050-1f8480382548', 'METHOD': 'BIT', 'SEQUENCE': 0, 'CONTENT': {'UDP_ADDRESS': ('192.168.0.200', 5710), 'PRICE': '20'}, 'SENDER_ADDRESS': ('192.168.0.200', 62404)}<br>
DEBUG:root:User input: end<br>
INFO:root:{'ID': 'e2e36f28-0c6a-491f-bfc1-e68c744d928b', 'METHOD': 'RMI', 'SEQUENCE': 0, 'CONTENT': {'METHODE': 'self.end_auction()'}, 'SENDER_ADDRESS': ('192.168.0.200', 62429)}<br>
DEBUG:root:$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$<br>
Auction ended successfully!<br>
Winner is af5bc12a-cca3-4856-a050-1f8480382548 with the price 20!<br>
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$<br>
DEBUG:root:[('230d743c-4f73-418e-82f9-04bb3d751a84', 10), ('af5bc12a-cca3-4856-a050-1f8480382548', 20)]<br>
</details><br>

### Progressing<br>
![broadcast](img/election.png) <br>
<b>27.11.2022:</b> tune the broadcast function. Gonna watch the Worldcup! 😊<br>
<b>28.11.2022:</b> multithread tested and added so that the system can handle multi-request.<br>
<b>03.12.2022:</b> realizing the multithread function. Now the model can automatically set up the udp_listen function. Optimize the structure of codes. New abstract function for auction component:`interface()`, `state_update()`
and some small gadgets. Broadcast logic finished! unused user function deleted! Now we have a fully functioning broadcast system!<br>
<b>04.12.2022:</b> Tiny bugs fixed. Now the clients can also use the `find` method to join a group via redirect. Implemented remote methode invocation with no returned value.<br>
<b>05.12.2022:</b> Dealt with the redundant request problem and optimize the structure. New function `assign()` to separate the main server logic with the servers. Finally! rmi works! Now the broadcast function is over and go into Bug test!<br>
<b>06.12.2022:</b> Make the terminal more beautiful<br>
<b>08.12.2022:</b> Add three new port for every process to handle specified task. Use pickle marshall instead of json to send out pandas file. Changed secrets to uuid4.<br>
<b>10.12.2022:</b> add new sequencer. preparation for totally ordered multicast.<br>
<b>11.12.2022:</b> Try broadcast on several physical machines and fixed the ip problem in WLAN situation. Deleted the message class merged it into Auction_component. Use `heapq` to maintain a min-Heap for the hold_back_queue implementation.<br> 
<b>13.12.2022:</b> First test on reliable multicast without negative acknowledgement. No time to do more because of worldcup!<br>
<b>14.12.2022:</b> Negative acknowledgement realized. Add a new user function `intercept`, but not tested. I think I can run the whole test on weekend. Worldcup tonight! <br>
<b>15.12.2022:</b> New component group_member_service(gms) to manage all the client/server list and heartbeat for both client and server. Going to Christmas markt tonight!<br>
<b>16.12.2022:</b> Finally the gms start to functioning! Tones of bugs fixed! New Added `utils.py` and `config.py` to make the code more clean and readable. Removed the code `message.py`, since the function is no longer needed.<br>
<b>17.12.2022:</b> Bit function online! Totally reliable multicast online! but not tested for message loss yet. And btw, i betrayed colorama, because i found rich more beautiful!<br>
<b>19.12.2022:</b> Add a batch file for testing. Fixed color issue caused by multi-threading.<br>
<b>21.12.2022:</b> New headless model and function_test.py. For the future experiment and testing. New global_time_sync.py module to synchronize the clock in the best effort (planning phase).
<b>24.12.2022:</b> New TUI developing... And merry christmas!!!<br>
<b>12.01.2023:</b> Fixed little bugs for broadcast in complex environment and bit function correction.<br>
<b>13.01.2023:</b> Added election functions! Start to look better!
<b>14.01.2023:</b> Fixed bugs in election and broadcasts. The subnet mask now is functioning on windows, test still need on linux pc.<br>
<b>15.01.2023:</b> Supplementary coding for gms and gts. Tested reliable ordered  multicast. Various bugs fixed.<br>
<b>16.01.2023:</b> merge some of the functions. Try to implement byzantine agreement part. Add return value function for the remote method invocation and add new multicast send wit response messages.<br>
![broadcast](img/failure_in_middle_bid.png) <br>
<b>18.01.2023:</b> I am soooo stupid.😡 Until today's lecture i realized that the multicast that I've used is group_unicast. So, I corrected it. Now we have the right one. And updated the RMI methode to and add some comments.<br>
<b>23.01.2023:</b> Refine election code. Move all the MAIN_SERVER part into the gms to separate the usages. Debugging. Tested multi failure possibilities and enable some degrees of failure management.<br>
<b>24.01.2023:</b> first time test on 4-server 4-client(and 4-server 8 client) situation and multiple machine. Not very good. Deliver a few bugs and did some code optimizations.<br> 
<b>25.01.2023:</b> dealt with the problem that the sequence synchronize problem for later joined processes.<br> 
<b>27.01.2023:</b> multiple bugs fixed! Tested on 12 Process in multiple physical devices and it worked like a charm! <br> 
<b>28.01.2023:</b> Added logging function and small bugs fixed.<br>
<b>29.01.2023:</b> Newly added phase king algorithm! To absolute resolve the byzantine. holpe to get 1.0<br>
<b>30.01.2023:</b> Project summary.<br>
<b>01.02.2023:</b> Get rid of the problem of hotspot disconnection simulation and fixed the netmask function(which matbe the reason why the tests failed in eduraum), recontructed some major function. Hope that is the last big movement for this project. ps: now the system can run without specify a mein server.<br>
<b>03.02.2023:</b> Various bugs fixed. <br>
<b>05.02.2023:</b> Election method and grooup member service fixed. <br>
<b>06.02.2023:</b> Added a little new feature to make the election part more robust under failure. A little bit nervous before the presentation. <br>
<b>07.02.2023:</b> At last i decided that the screen still need some colors, so i implemented a method to make it look good. Hope everthing be fine in the demo!<br>
<b>07.02.2023:</b> Final push. Good luck everyone!<br>
### TODO<br>
1. ~~bugs fix!!!!!!!!~~
2. ~~BIG PROBLEM: I don't know how to add emoji in markdown!!~~