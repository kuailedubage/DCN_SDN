基于SDN技术的Fat-tree与Bcube网络模拟与试验床搭建
--------------------------------
安装
----------------
  - 执行sudo mininet/util/install.sh -nfv安装Mininet及OpenvSwitch
  - POX直接使用无需安装
  - 分别进入ripl和riplpox根目录执行sudo python setup.py install安装依赖



Part1
----------------
> - 先启动mininet，构造k-ary fattree --topo ft,<交换机端口数k>,< r:1,k/2需要被r整除>  
 
>   $sudo mn -- custom ~/DCN_SDN/ripl/ripl/mn.py --topo ft,4,1 --controller=remote --mac 
 
>   $sudo mn --custom ~/DCN_SDN/ripl/ripl/mn.py --topo ft,4,2 --controller=remote --mac



> - mininet构造好topo后，再启动pox控制器 --topo=ft,<与上面mininet保持一致>,<与上面mininet保持一致>

>   $cd ~/DCN_SDN/pox

>   $./pox.py riplpox.riplpox --topo=ft,4,1 --routing=spath --mode=reactive samples.pretty_log

>   $./pox.py riplpox.riplpox --topo=ft,4,2 --routing=spath --mode=proactive samples.pretty_log
>
> - 如上相应参数换成 --topo bc,k,n 则构建BCube topo ------------ k:层数，n:BCube0所含servers数
    更改路由算法参考routing.py中的DCRouting类并修改riplpox目录下的util.py文件中的ROUTING字典。

Part2
----------------
> - 将Part1的riplpox.riplpox换成riplpox.TestBedController启动测试床控制器，此处无需指定--topo参数，仅支持reactive模式，改变试验床交换机拓扑或连接端口需要重新配置dctopo.py中的拓扑类并修改TestBedController.py中的相关配置。更改主机位置和数量无需修改文件。更改HP E3800交换机时注意与控制器命名规则映射保持一致。
