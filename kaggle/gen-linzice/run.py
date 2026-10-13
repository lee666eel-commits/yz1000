# yzqj -- 林子策 full font, step 1 of 2 (10-14). He picked "N=100, 1000 steps" from the minchars test
# (kaggle/finetune-linzice). That checkpoint was not kept, so retrain it exactly (same 100-char prefix of
# train_order_linzice.txt, ckpt_ft start, seed 123, 1000 steps), then generate every 通用规范汉字表一级 char
# he has not written (3240 = 3500 minus his 263 real CJK; 境 he blacked out, so it is generated).
# Also regenerates the 40 held-out chars so the per-person --yscale for build_full_font.py can be MEASURED
# against his real glyphs (do not reuse another participant's constant).
# Char list embedded (base64) because `kernels push` ships only this file.
# Push: kaggle kernels push -p D:/handwriting-font/kaggle/gen-linzice
import os, sys, glob, subprocess, functools, shutil, time, base64, zipfile

WORK = "/tmp/FontDiffuser"
OUT = "/kaggle/working/outputs"
STYLE = "LinZiCe"
N, STEPS, CELL = 100, 1000, 96
REF_CH = "堂"
Q, NL = chr(34), chr(10)
TODO = list(base64.b64decode("5LiA5LmZ5Y2B5LiB5Y6C5LiD5Y2c5YWr5Lq65YS/5YyV5Yeg5Lmd5YiB5LqG5YiA5LmD5Y+I5bmy5LqO5LqP5Zyf5omN5LiL5a+45aSn5LiI5LiH5LiK5bCP5Y+j5bGx5be+5Y2D5Lme5bed5Lq/5Liq5aSV5LmF5LmI5Yu65Yeh5Li45Lqh6Zeo5Lir5LmJ5LmL5bC45bex5bey5bez5byT5a2Q5Y2r5Lmf5YiD6aOe5Y+J5Lmh5Liw546L5byA5LqV5aSp5aSr5YWD5peg5LqR5LiQ5omO5pyo5Y6F5LiN54qs5aSq5Y6G5q255Y+L5bCk5Yy56L2m5beo54mZ5bGv5oiI5LqS5YiH55Om5q2i5bCR5puw5pel5Lit6LSd5YaI5YaF6KeB54mb5omL5q+b5aOs5aSt5LuB5LuA54mH5LuG5LuH5biB5LuN5pak54iq5Y+N5LuL54i25LuO5LuR5LuK5Ye25LmP5LuT5rCP5Yu/5qyg6aOO5Li55YyA5LmM5Yu+5Yek5YWt5Lqi5pa554Gr5Li65b+G6K6h6K6i5oi35YaX6K6l5b+D5bC65byV5LiR5be05a2U5Yqe5Lul5YWB5LqI6YKT5Yqd5Y+M5Lmm5bm7546J5YiK5pyr5Ye75omT5ben5omR5Y2J5omS5omU5Y6755SY6Im+5Y+k5Y+v5LiZ5bem5Y6J55+z5Y+z5biD5aSv5oiK6b6Z54Gt6L2n5Lic5Y2h5YyX5Y2g5Ye45Y2i5Lia5pen5biF5b2S5pem55uu5LiU5Y+255Sy55Sz5Y+u55S15Y+355Sw55Sx5Y+q5Y+t5aSu5YWE5Y+95Y+85Y+r5Y+p5Y+o5Y+m5Y+55YaJ55q/5Ye55Zua5Zub55Sf55+i5aSx5LmN56a+5LiY5LuY5LuX5LuZ5Lus5Luq55m95LuU5LuW5pal55Oc5LmO5Lib55So55Sp5Y2w5bCU5LmQ5Y+l5YyG5YaM5Y2v54qv5aSW5Yas6bif5Yqh6aWl5Li75biC56uL5Yav546E6Zeq5YWw5Y2K5rGB5aS05rGJ5a6B56m05a6D6K6o5YaZ6K6t6K6u5b+F6K6v5rC45Y+45bC85byX5byY5Ye66L695aW25aW05Y+s5Yqg55qu5a2V5Y+R5Zyj5a+55Y+w55+b57qg5bm85Lid6YKm6L+C5YiR5oiO5omb5a+65ZCJ5omj5omY5bep5Zy+5omn5omp5omr5Zyw5oms6ICz6IqL6IqS5Lqa6Iqd5py95py05py65p2D6L+H6Iej5ZCP5Y2P6KW/5Y6L5Y6M5oiM5Zyo55m+5pyJ5a2Y6ICM6aG15Yyg5aS45aS654Gw6L6+5YiX5q275oiQ5aS55aS36L2o6YKq5bCn5YiS6Iez6LSe5biI5bCY5bCW5Yqj5YWJ5b2T5pep5ZCQ5ZCT6Jmr5puy5ZCV5ZCK5ZCD5Zug5ZC45ZCX5ZCG5bG/5bG55bKB5biG5Zue5bKC5Yia572R6IKJ5bm05pyx5Lii5bu36IiM56u56L+B5LmU6L+E5Lyf5LmS5LmT5LyR5LyN5LyP5LyY6Ie85LyQ5bu25Luy5Lu25Lyk5Lu35Lym5Lu95Y2O5Luw5LyZ5Lyq6Ieq5LyK6KGA5ZCR5Ly85ZCO6Iif5Lya5p2A5LyB5LyX54i35Lye5Yib6IKM6IKL5py15p2C5Y2x5pes5peo5pet6LSf5YyI5aSa5LqJ5aOu5Yay5aaG5Yaw5bqE5Lqm5YiY6b2Q5Lqk6KGj5Lqn5Yaz5Lql5YWF5aaE6Zet6Zev576K5YWz57Gz54Gv5bee5rGX5rGh5rGf5rGb5rGg5rGd5rGk5b+Z5YW05a6H5a6I5a6F5a2X6K6y6K6z5Yab6K626K646K656K666K685Yac6K696K6+6K6/6K+A5a+76YKj6L+F5bC95byC5byb5a2Z6Zi16Ziz5pS26Zi26Zi06Ziy5aW45aaC5aaH5aaD5aW95aW55aaI5oiP57695Lmw57qi6amu57qk6amv57qm6amw57qr5beh5a+/5byE6bqm546W546b5b2i5oiS5ZCe6L+d6Z+n5om25oqa5Z2b5Z2P5oqg5omw5om85ouS5om+5Z2A5omv5oqE6LSh5rGe5Z2d5pS76LWk5oqY5oqT5omz5oqh5omu5oqi5a2d5Z2O5oqR5oqb5oqV5Z2f5Z2R5oqX5Z2K5oqW5oqk5aOz5b+X5Z2X5omt5oqK5oql5ouf5Y205oqS5Yqr6IqZ6Iqc6IuH6Iq96Iqx6Iq56Iql6Iqs6IuN6Iqz6Iqm6Iqv5Yqz6Iqt6IuP5p2G5p2g5p2c5p2Q5p2R5p2W5p2P5p2J5ber5p2O5p2o5rGC55Sr5Yyj5p2f5ZC+6LGG6YWJ5Li95Yy76L6w5ZCm6L+Y5bCs5q285p2l6L+e6L2p5Y2k6IKW5pex55uv5ZGI5pe25ZC05Yqp5Y6/6YeM5ZGG5ZCx5ZCg5ZGV5pe35Zu05ZGA5ZCo6Laz6YKu55S35Zuw5ZC15Liy5ZGQ5ZCs5ZCf5ZCp5ZGb5ZC75ZC55ZGc5ZCt5ZCn6YKR5ZC85Zuk5Yir5ZCu5bKW5bKX5biQ6LSi6ZKI6ZKJ54mh5ZGK5oiR5Lmx5Yip56eD56eA56eB5q+P5YW15Lyw5L2V5L2Q5L2R5L2G5Ly45L2D5L2c5Lyv5Ly25L2j5L2O5L2g5L2P5L2N5Ly055qC5Ly65L2b5Zux6L+R5b275b256L+U5L2Z5Z2Q6LC35aal5ZCr6YK75bKU6IKd6IKb6IKa6IKY6IKg6b6f55S45YWN54uC54q554uI6KeS5Yig5p2h5b2k5Y2154G45bKb5Yio6L+O6aWt6aWu57O76KiA5Ya754q25Lqp5Ya15bqK5bqT5bqH55aX5ZCd5bqU6L+Z5Ya35bqQ5bqP6L6b5byD5Ya25b+Y6Zew6Zey6Ze35Yik5YWR54G254G/54G85byf5rGq5rKQ5rKb5rGw5rKl5rKZ5rG95rKD5rKm5rG55rOb5rKn5rKh5rKq5rKI5rKJ5rKB5oCA5b+n5b+x5a6M5a6L54mi56m256m354G+6Imv6K+B5ZCv6K+E6KGl56WA6K+G6K+I6K+J572V6K+K6K+N6K+R5ZCb54G15Y2z5bGC5bGB5bC/5bC+6L+f5bGA5pS55b+M6ZmF6ZmG6Zi/6ZmI6Zi76ZmE5Z2g5aaT5aaZ5aaW5aeK5aao5aaS5Yqq5b+N5Yqy55+j6bih57qs6amx57qv57qx57qy57qz6amz57q157q357q457q557q66am057q95aWJ546p5q2m6Z2S6LSj546w546r6KeE5oq55Y2m5Z235Z2v5oui5ouU5Z2q5ouj5Z2m5ouF5Z2k5oq85oq95ouQ5ouW5ouN6aG25ouG5ouO5oq15ouY5Yq/5oqx5ouE5Z6D5ouJ5oum5bm45ouM5oun5ouC5ouZ5oub5oqr5ouo5oup5oqs5ouH5ouX5YW25Y+W6IyJ6Ium5piU6Iub6Iul6IyC6Iu56IuX6Iux6Iuf6IuR6Iue6IyD55u06IyB6IyE6IyO6IuU6IyF5p6J5p6X5p6d5p2v5p6i5p+c5p6a5p6Q5p2/5p2+5p6q5p6r5p6E5p2t5p2w6L+w5p6V5Lin5Y2n5LqL5Yi65p6j6Zuo5Y2W6YOB55++55+/56CB5Y6V5aWI5aWU5aWH5aWL5oCB5qyn5q605Z6E5aa76L2w6aG36L2s5pap6L2u6L2v5Yiw6Z2e5Y+U5q2n6IKv6b2/5Lqb5Y2T6JmO6JmP6IK+6LSk5bCa5pe65ZGz5p6c5piG5Zu95ZOO5ZKV5piM5ZG155WF5piO5piT5ZKZ5piC6L+q5Zu65b+g5ZG75ZKS5ZKL5ZKQ5ZG85ZKP5ZGi5ZKE5ZKW5bK45bKp5biW572X5bic5biV5bKt5Yev6LSl6LSm6LSp6LSs6LSt6LSu5Zu+6ZKT55+l6L+t5rCb5Z6C54mn54mp5LmW5Yiu56eG5ZKM5a2j5aeU56eJ5L2z5L6N5bKz5L6b5L2/5L6L5L6g5L6l5L6E5L6m5L6j5L6n5Yet5L6o5L2p6LSn5L6I5L6d5Y2R55qE6L+r6LSo5qyj5b6A54is5b285b6E6IiN5Yi55ZG96IK05pan54i46YeH6KeF5Y+X5Lmz6LSq6LSr5b+/6IKk6IK66IKi6IK/6IOA5pyL6IKh6IKu6IKq6IKl5pyN6IOB5piP6bG85YWU54uQ5b+954uX54ue5aSH6aWw6aWx6aWy5Y+Y5Lqs5bqe5bqX5aSc5bqZ5bqc5bqV55af55aZ55aa5YmC5Y2S6YOK5bqa5bqf5YeA55uy5pS+5rCT6Ze46Ze55Yi45Y235Y2V54Ks54KS54KK54KV54KO54KJ5rKr5rWF5rOV5rOE5rK95rKz5rK+5rOq5rKu5rK55rOK5rK/5rOh5rOj5rOe5rO75rOM5rOz5rOl5rK45rK85rOi5rO85rO95rK75oCU5oCv5oCW5oCn5oCV5oCc5oCq5oCh5a2m5a6d5a6X5a6a5a6g5a6c5a6h5a6Z5a6Y56m65biY5a6b6K+V6YOO6K+X6IKp5oi/6K+a6KGs6KGr6KeG56WI6K+d6K+e6K+h6K+i6K+l6K+m6IKD6Zq25bia5bGJ5bGF5bGK5Yi35bGI5byn5byl5bym5a2f6ZmL6ZmM5a2k6ZmV6ZmN5Ye96ZmQ5aa55aeR5aeT5aeG6L+i6am+5Y+B6Imw57q/57uD57uF57uG6am257uH6am557uI6am757uK6am857uN57uO57uP6LSv5aWR6LSw5aWP5pil5biu546354+N546y54+K54675q+S5Z6L5out5oyC5bCB5ou35oux5Z6u5oyO5Z+O5oyf5oyg5pS/6LW15oyh5ou95ZOJ5oy65ous5Z6i5ou05ou+5oyR5Z6b5Z6r5oyj5oyk5ou85oyW5oyl5oyq5ouv5p+Q55Sa6I2G6Iy46Z2p6Iys6I2Q5be35bim6I2J6Iyn6Iy16Iy26I2S6Iyr6I2h6I2k6I2n5pWF6IOh6I2r6I2U5Y2X6I2v5qCI5p+R5p6v5p+E5qCL55u45p+l5p+P5qCF5p+z5p+x5p+/5qCP5p+g5qCR5YuD6KaB5p+s5ZK45aiB5q2q56CU56CW5Y6Y5Y6a56CM56CC5rO156Ca56CN6Z2i6ICQ6ICN54m16bil5q6L5q6D6L206L276bim55qG6Z+t6IOM5oiY6JmQ5Li06KeI56uW55yB5YmK5bCd5pin55u55piv55u855yo5ZOH5ZOE5ZOR5pi+5YaS5pif5pio5ZKn5pit55WP6La06IOD6LS155WM6Jm56Jm+6JqB5oCd6JqC6Jm95ZOB5ZK96aqC5YuL5ZOX5ZKx5ZON5ZOI5ZOG5ZKs5ZKz5ZKq5ZOq5ZOf54Kt5bOh572a6LSx6LS06LS76aqo5bm96ZKZ6ZKd6ZKe6ZKi6ZKg6ZKl6ZKm6ZKn6ZKp6ZKu5Y2457y45ouc55yL55+p5q+h5rCi5oCO54my6YCJ6YCC56eS6aaZ56eN5aSN56u/5q615L6/5L+p6LS36aG65L+u5L+P5L+d5L+D5L+E5L+Q5L6u5L+t5L+X5L+Y5L+h55qH5rOJ6ay85L6156a55L6v6L+95L+K55u+5b6F5b6K6KGN5b6L5b6I6aG75Y+Z5YmR6YCD6aOf55uG6IOa6IOn6IOG6IOc6IOe6IOW6ISJ6IOO5YuJ54ut54uu54us54uw54uh54ux54ug6LS45oCo5oCl6aW16aW26JqA6aW66aW85bOm5byv5ZOA5Lqt5Lqu6L+55bqt55au55av55ar55ak5ZKo5ae/6Z+z5bid5pa96Ze66Ze76Ze96ZiA5beu5aec5Y+b6YCB57G76L+357G95aiE5YmN6aaW6YCG5YW55oC754K854K454OB54Ku54Kr54OC5YmD5rS85rSq5rSS5p+S5rWH5rWK5rSe5rWL5rSX5rS+5rS95p+T5rSb5rWP5rWO5rSL5rSy5rWR5rWT5rSl5oGD5oGS5oGi5oGN5oGs5oGk5oGw5oG85oGo5Li+6KeJ5a6j5a6m5a6r5a6q56qB56qD5a6i6K+r6K+s6K+t5omB6KKE56WW56We56Wg6K+v6K+x6K+y6K+06K+15Z6m6YCA5pei5bGL5pi85bGP5bGO6LS56Zmh6YCK55yJ6Zmo6Zmk6Zmp6Zmi5aiD5ael5aeo5ae75aiH5aea5aic5oCS5p626LS655uI5YuH5oCg55m46Jqk5p+U5Z6S57uR57uT57uV6aqE57uY57ua6aqG57uc57ud57ue6aqH57uf6ICV6ICY6ICX6ICZ6Imz5rOw56em54+g5Yy/6JqV6aG955uP5Yyq5o2e5qC95o2V5Z+C5o2C5oyv6L296LW26LW355uQ5o2O5o2N5o2P5Z+L5o2J5o2G5o2Q5o2f6KKB5o2M6YO96YCd5o2h5oyr5o2i5oy95oya54Ot5oGQ5o2j5aO25o2F5Z+D5oyo6IC76IC/6IC96IGC5oGt6I696I6x6I6y6I6r6I6J6I235pmL5oG26I656I665qGG5qKG5qGC5qGU5qCW5qGj5qGQ5qCq5qGl5qGm5qCT5qGD5qC85qGp5qCh5qC45qC35qC557Si5ZOl6YCX5qCX6LS+6YWM6YWN57+F6L6x5ZSH5aSP56C456Cw56C+56GA56C05Y6f5aWX6YCQ54OI5q6K5q6J6aG+6L2/6L6D6aG/5q+Z6Ie05p+05qGM6JmR55uR57Sn5YWa6YCe5pmS55yg5pmT5ZOu5ZSg6bit5pmD5ZO65pmM5YmU5pmV6JqM55WU6Jqj6JqK6Jqq6JqT5ZOo5ZOp5ZyD5ZOt5ZOm6biv5ZSk5ZSB5ZO85ZSn5ZWK5ZSJ5ZSG572i5bOt5bOo5bOw5ZyG5bO76LS86LS/6LWC6LWD6ZKx6ZKz6ZK76ZK+6ZOB6ZOD6ZOF57y65rCn5rCo54m554m65LmY5pWM56ek56ef56ev56en56ep56eY6YCP56yU56yR56yL5YC65YCf5YC85YCa5L+65YC+5YCS5YCY5L+x5YCh5YCZ6LWB5L+v5YCN5YCm5YGl6Iet5bCE6Lqs5oGv5YCU5b6S5b6Q5q636Iiw6Iix6Iis6Iiq6YCU5ou/6IC454i56IiA54ix6LG66LG56aKB6aKC57+B6IOw6ISG6ISC6IO46IOz6ISP6ISQ6IO26ISR6IST6YCb54u454u85Y2/6YCi6bi155WZ6biz55qx6aW/6aaB5YeM5YeE5oGL5qGo5rWG6KGw6KG36YOt5bit55eH55eF55a+5paL55a555a855ay6ISK5pWI56a757SK5ZSQ55O35YeJ56uZ5YmW56ue6YOo5peB5peF55Wc6ZiF576e576U55O25ouz57KJ5paZ5YW854Ok54OY54Om54On54Ob54Of54OZ6YCS5rab5rWZ5rad5rWm6YWS5raJ5raI5rah5rWp5rW35raC5rW05rWu5raj5rak5rWB5ram5ran5raV5rWq5rW45rao54Or5rap5raM5oKW5oKf5oKE5oKN5oKU5oKv5oKm5a6z5a695a615a605a6+56qN56qE5a655a6w5qGI5pyX6K+46K+65omH6K+96KKc6KKW6KKN56Wl5Yal5Yak6LCF6LCG6LCI6LCK5Yml5oGz5Ymn5bGR5byx6Zm156Wf6Zm26Zm36Zmq5aix5aif5oGV5ail5aiY6YCa6IO96Zq+6aKE5qGR57ui57uj6aqM57un6aqP55CD55CQ55CJ55CF5o2n5aC15o6q5o+P5Z+f5o265o6p5o235o6S54SJ5o6J5o226LWm5aCG5Z+g5o6A5o6I5o275pWZ5o6P5o6Q5o6g5o6C5o6l5o635o6n5o6i5o2u5o6Y5o665Z+66IGG5YuY6IGK5ai26JGX6I+x5YuS6I+y6JCM6JCd6I+M6JCO6I+c6JCE6I+K6I+p6JCN6I+g6JCk5Lm+6JCn6JCo6I+H5qKw5b2s5qKm5amq5qKX5qKn5qKi5qKF5qOA5qKz5qKv5qG25qKt5pWR5pu55Ymv56Wo6YWd6YWX5Y6i5oia56GF56GV5aWi55uU54i96IGL6KKt55ub5Yy+6Zuq6L6F6L6G6aKF6Jma5b2q6ZuA55y25YyZ5pmo552B55yv55y85oKs6YeO5ZWq5ZWm5pmm5pma5ZWE5ZWh6Led6La+5ZWD6LeD55Wl6Jqv6JuA6JuH5ZSs57Sv6YSC5ZSx5oKj5ZWw5ZS+5ZSv5ZWk5ZWl5ZW45bSW5bSO5bSt6YC75bSU5bi35bSp5bSH5bSb5am05ZyI6ZOQ6ZOb6ZOd6ZOc6ZOt6ZOy6ZO255+r55Sc56e45qKo54qB56e956e756yo56y856yb56yZ56ym5pWP6KKL5oKg5YG/5YG25YGO5YG35oKo5ZSu5YGc5YGP6Lqv5YWc5YGH6KGF5b6Y5b6Z5b6X6KGU55uY6Ii26Ii56Ii15pac55uS6bi95pWb5oKJ5qyy6ISa6ISW6ISv6LGa6IS46ISx5aSf54yc54yq54yO54yr5Yew54yW54yb56Wt6aaF6aaG5YeR5YeP5q+r54O55bq26bq75bq155eK55eS55eV5buK5bq35bq46bm/55uX56ug56uf5ZWG5peP5peL5pyb546H6ZiO6ZiQ552A576a55y357KY57KX57KS5pat5Ymq5YW954SK54SV5re76bi/5reL5rav5re55rig5reR5reM5re35reu5reG5riK5rer5riU5reY5rez5ray5rek5reh5reA5rau5ra15amG5qKB5riX5oOF5oOc5oOt5oK85oOn5oOV5oOf5oOK5oOm5oK05oOL5oOo5oOv5a+H5a+F5a+E5a+C5a6/56qS56qR5a+G6LCL6LCN6LCO6LCQ6KKx56W356W46LCT6LCa6LCc6YCu5pWi5bCJ5bGg5by56ZqL5aCV6ZqP6ZqF6ZqG6ZqQ5ama5am25amJ6aKH6aKI57up57uq6aqR57uw57uz57u057u157u357u457u857u957yA5bei55C055Cz55Ci55C85paR5pu/5o+N5qy+5aCq5aGU5pCt5aCw5o+p6LaK6LaB6LaL6LaF5o+95aCk5o+t5b2t5o+j5o+S5o+q5pCc54Wu5o+05pCA6KOB5pCB5pCT5pCC5pCF5aO55o+h5pCU5o+J5pav5qy66JGr5pWj5oO56JGs5Yuf6JGb6JGh5pWs6JGx6JKL6JKC6JC96Z+p5pyd6L6c6JG15qOS5qOx5qOL5qSw5qSN5qOu54Sa5qSF5qSS5qO15qON5qSO5qOJ5qOa5qOV5qO65qaU5qSt5oOg5oOR6YC857Kf5qOY6YWj6YWl5Y6o5Y6m56Gs56Gd56Gu56Gr6ZuB5q6W6KOC6ZuE6aKK6Zuz5pqC57+Y6L6I5oKy57Sr5Ye/6L6J5pWe5qOg6LWP5o6M5pm0552Q5pqR5pyA5pmw6YeP6byO5Za35Zaz5pm25ZaH6YGH5ZaK6YGP5pm+5pmv55W06Le16LeL6LeM6LeR6Leb6YGX6JuZ6Jub6JyT6JyS6Juk5Zad6bmD5ZaC5ZaY5ZaJ5Za75ZW85Zan5bWM5bmF5bi96LWL6LWM6LWO6LWQ6LWU6buR6ZO46ZO66ZO+6ZSA6ZSB6ZSE6ZSF6ZSI6ZSL6ZSM6ZSQ55Sl5o6w55+t5pm65rCu5q+v5rCv6bmF5Ymp56iN56iA56iO562Q562J562R562W562b562S562P562U562L562d5YKy5YKF54mM5aCh6ZuG54Sm5YKN5YKo55qT55qW57Kk5aWl6KGX5oOp5b6h5b6q6ImH6IiS6YC+55Wq6YeK56a96IWK6IS+6IWL6IWU6IWV6bKB54yp54ys54y+54y05oOr54S26aaI6aaL6Juu5bCx5pWm5paM55eY55ei55eq55eb56ul56uj6ZiU5ZaE57+U576h5pmu57Kq5bCK5aWg6YGT6YGC5pu+54Sw5riv5rue5rmW5rmY5rij5rik5ri65rm/5ri05rqD5rqF5ruR5rmD5rid5rih5ruL5riy5rqJ5oSk5oWM5oOw5oSV5oSj5oO25oSn5oSJ5oWo5Ymy5a+S5a+M5a+T56qc56qd56qW56qX56qY6YGN6ZuH6KOV6KOk6KOZ56aF56aE6LCi6LCj6LCk6LCm54qA5bGe5bGh5by657Kl55aP6ZqU6ZqZ6ZqY5aqS57Wu5auC5aqa5am/57yF57yG57yJ57yO57yT57yU57yV6aqX57yW6aqa57yY55Gf6bmJ55Ge55Gw55GZ6IKG5pGE5pG45aGr5pCP5aGM6byT5pGG5pC65pCs5pGH5pCe5aGY5pGK6IGY5paf6JKc5Yuk6Z206Z226bmK6JOd5aKT5bmV6JOs6JOE6JKy6JOJ6JKZ6JK454yu5qS/56aB5qWa5qW35qaE5oOz5qeQ5qaG5qW85qaC6LWW6YWq6YWs56KN56KY56KR56KO56Kw56KX56KM5bC06Zu36Zu26Zu+6Zu56L6Q6L6R6L6T552j6aKR6b6E6Ym0552b5525552m556E552r552h552s5Zec6YSZ5Zem5oSa5pqW55uf5q2H5pqX5pqH54Wn55W46Leo6Le36Lez6Le66Leq6Lek6Lef6YGj6JyI6JyX6Ju+6JyC6JyV5ZeF5Zeh5ZeT572y572u572q572p6JyA5bmM6ZSZ6ZSa6ZSh6ZSj6ZSk6ZSl6ZSm6ZSv6ZSw55+u6L6e56ia56ig6aKT5oSB5625562+566A56235q+B6IiF6byg5YKs5YK75YOP6Lqy6a2B6KGZ5b6u5oSI6YGl6IW76IWw6IWl6IWu6IW56IW66bmP6IW+6IW/6bKN54y/6aKW6Kem6Kej54We6ZuP6aaN6aaP6YWx56aA55e55buT55e055ew5buJ6Z2W6Z+16KqK57Ku5pWw54WO5aGR5oWI54Wk54WM5ruh5ryg5ruH5ruk5rul5ruU5rqq5rqc5ryT5rua5rqi5rqv5ruo5rq25rq657Kx5rup5oWO6KqJ5aGe5a+e56ql56qf5a+d6KSC6KO46LCs576k5q6/6L6f6Zqc5aqz5auJ5auM5auB5Y+g57ya57yd57yg57yk5Ym/6Z2Z56Kn55KD6LWY54as5aKZ5aKf5ZiJ5pGn6LWr6KqT5aKD5pGY5pGU5pKH6IGa5oWV5pqu5pG56JST6JSR6JSh6JSX6JS96JS854aZ6JSa5YWi5qih5qeb5qa05qac5qao5qaV6YGt6YW16YW36YW/6YW456Kf56Kx56Kz56OB6ZyA6L6W6L6X6ZuM6KOz6aKX556F5aKF5Ze96LiK6Jy76Jyh6J2H6JyY6J2J5Zib5ZiA6LWa6ZS56ZS76ZWA6Iie6IiU56iz54aP566V566X566p566r6IiG5YOa5YOn6by76a2E6a2F6LKM6Iac6IaK6IaA6bKc55aR5a216aaS6KO55pWy6LGq6IaP6YGu6IWQ55ip55if55im6L6j5b2w56ut56uv5peX57K55q2J5byK54aE54aU54W95r2H5ryG5ryx5ryC5ru05ry+5ryP5oWi5oW35a+o5a+h5a+f6Jyc5a+l6LCt6IKH6KSQ6KSq6LCx6Zqn5aup57+g54aK5Yez6aqh57yp5oWn5pK15pKV5pKS5pKp6Laj6Laf5pKR5pKu5pKs5pKt5pOS5aKp5pKe5pKk5aKe5pKw6IGq6Z6L6Z6N6JWJ6JWK6JSs5qiq5qe95qix5qmh5qif5qmE5pW36LGM6aOY6YaL6YaH6YaJ56OV56OK56OF56K+6ZyH6ZyE6ZyJ556S6aKY5pq0556O5Zi75Zi25Ziy5Zi55b2x6Lii6LiP6Lip6Liq6J226J206J2g6J2O6J2M6J2X6J2Z5Zi/5Zix5bmi5aKo6ZWH6ZWQ6ZWR6Z2g56i956i76buO56i/56i8566x56+T566t56+H5YO16Lq65YO76ImY6Iad6Iab6bKk6bKr54af5pGp6KSS55iq55ik55ir5Yeb6aKc5q+F57OK6YG15oaL5r2c5r6O5r2u5r2t6bKo5r6z5r2Y5r6I5r6c5r6E5oeC5oaU5oeK5oaO57+p6KSl6LC06bmk5oao5YqI5bGl6LGr57yt5pK85pOC5pON5pOF6JW+6Jav6Jab6JaH5pOO6Jaq6JaE6aKg57+w5Zmp5qmx5qmZ5qmY5pW06J6N55Oi6YaS6ZyN6ZyO6L6Z5YaA5Zi06Lix6LmE6LmC6J+G6J6D5Zmo5Zmq6bmm6LWg6buY6buU6ZWc6LWe56mG56+u56+h56+356+x5YSS6KGh6Iao6ZuV6bK456Oo55i+55i45Yed6L6o6L6p57OZ57OW54eD5r+S5r6h5r+A5oeS5oa+5oeI56q/5aOB6YG/57yw57y05oi05pOm6JeJ6Z6g6JeP6JeQ5qqs5qqQ5qqA56SB56O36Zyc6Zye556t556n556s556z556p556q5puZ6LmL6LmI6J666J+L6J+A5ZqO6LWh56mX6a2P57Cn57CH57mB5b6954i15pym6IeK6bOE55mM6L6r6LWi57Of57Og54el5oem6LGB6IeA6IeC57+86aqk6JeV6Z6t6Jek6KaG55676Lmm5Zqj6ZWw57+76bON6bmw54CR6KWf55Kn5oiz5a296K2m6JiR6Je75pSA5pud6Lmy6Lmt6Lms5beF57C457C/6J+56aKk6Z2h55mj55Oj57656bOW54iG55aG6ayT5aOk6aao6ICA6LqB6KCV5Zq85Zq35beN6bOe6a2U57Ov54GM6K2s6KCi6Zy46Zyy6Zy56LqP6buv6auT6LWj5ZuK6ZW255Ok572Q55+X").decode("utf-8"))
assert len(TODO) == 3240, len(TODO)


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


DS = NOTO = CKPT_FT = None
for root, dirs, files in os.walk("/kaggle/input"):
    if "heldout_linzice.txt" in files:
        DS = root
    if "NotoSansSC.ttf" in files and NOTO is None:
        NOTO = f"{root}/NotoSansSC.ttf"
    if root.endswith("ckpt_ft") and "unet.pth" in files:
        CKPT_FT = root
assert DS and NOTO and CKPT_FT, (DS, NOTO, CKPT_FT)
print("DS", DS, "| noto", NOTO, "| ft", CKPT_FT, flush=True)
os.makedirs(OUT, exist_ok=True)

import torch
assert torch.cuda.is_available(), "no CUDA"
if not os.path.isdir(WORK):
    run(["git", "clone", "--depth", "1", "https://github.com/yeungchenwa/FontDiffuser.git", WORK])
run([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
     "diffusers", "accelerate", "pyyaml", "pygame", "opencv-python-headless",
     "info-nce-pytorch", "kornia", "gdown", "tensorboard"])
os.makedirs(f"{WORK}/ckpt", exist_ok=True)

tp = f"{WORK}/train.py"
t = open(tp, encoding="utf-8").read()
if "INIT_CKPT_DIR" not in t:
    t = t.replace("import torch" + NL, "import torch" + NL + "import functools" + NL + "torch.load = functools.partial(torch.load, weights_only=False)" + NL, 1)
    anchor = "    model = FontDiffuserModel("
    assert anchor in t
    init_block = NL.join([
        "    if os.environ.get(@INIT_CKPT_DIR@):",
        "        _d = os.environ[@INIT_CKPT_DIR@]",
        "        unet.load_state_dict(torch.load(f@{_d}/unet.pth@))",
        "        style_encoder.load_state_dict(torch.load(f@{_d}/style_encoder.pth@))",
        "        content_encoder.load_state_dict(torch.load(f@{_d}/content_encoder.pth@))",
        "        print(@initialised from@, _d, flush=True)",
        ""]).replace("@", Q)
    t = t.replace(anchor, init_block + anchor, 1)
    open(tp, "w", encoding="utf-8").write(t)

uname = lambda ch: f"U{ord(ch):04X}"
heldout = list(open(f"{DS}/heldout_linzice.txt", encoding="utf-8").read().strip())
order = list(open(f"{DS}/train_order_linzice.txt", encoding="utf-8").read().strip())
tgt = lambda ch: f"{DS}/data/train/TargetImage/{STYLE}/{STYLE}+{uname(ch)}.jpg"
assert REF_CH in order[:N]

# --- retrain N=100 exactly as minchars v1
root = "/tmp/data_n100"
os.makedirs(f"{root}/train/TargetImage/{STYLE}", exist_ok=True)
if not os.path.exists(f"{root}/train/ContentImage"):
    os.symlink(f"{DS}/data/train/ContentImage", f"{root}/train/ContentImage")
for ch in order[:N]:
    p = f"{root}/train/TargetImage/{STYLE}/{STYLE}+{uname(ch)}.jpg"
    if not os.path.exists(p):
        os.symlink(tgt(ch), p)
env = dict(os.environ, INIT_CKPT_DIR=CKPT_FT, PYTHONUNBUFFERED="1")
run([sys.executable, "train.py", "--seed=123", "--experience_name=ft_n100",
     f"--data_root={root}", "--output_dir=/tmp/ft_n100", "--report_to=tensorboard",
     "--resolution=96", "--style_image_size=96", "--content_image_size=96",
     "--content_encoder_downsample_size=3", "--channel_attn=True",
     "--content_start_channel=64", "--style_start_channel=64",
     "--train_batch_size=8", "--perceptual_coefficient=0.01", "--offset_coefficient=0.5",
     f"--max_train_steps={STEPS}", f"--ckpt_interval={STEPS}", "--gradient_accumulation_steps=1",
     "--log_interval=50", "--learning_rate=1e-5", "--lr_scheduler=constant",
     "--lr_warmup_steps=0", "--drop_prob=0.1", "--mixed_precision=no"], cwd=WORK, env=env)
CK = f"/tmp/ft_n100/global_step_{STEPS}"
assert os.path.exists(f"{CK}/unet.pth"), CK
keep = "/kaggle/working/ckpt_linzice_n100"
os.makedirs(keep, exist_ok=True)
for f in ["unet.pth", "style_encoder.pth", "content_encoder.pth"]:
    shutil.copy(f"{CK}/{f}", f"{keep}/{f}")

# --- generate
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.chdir(WORK)
sys.path.insert(0, WORK)
torch.load = functools.partial(torch.load, weights_only=False)
import sample  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

font = ImageFont.truetype(NOTO, 100)   # same content recipe as finetune-data ContentImage (fitted 09-20)
CDIR = "/tmp/content"
os.makedirs(CDIR, exist_ok=True)


def render_content(ch):
    p = f"{CDIR}/{uname(ch)}.png"
    if not os.path.exists(p):
        im = Image.new("L", (128, 128), 255)
        d = ImageDraw.Draw(im)
        l, t_, r, b = d.textbbox((0, 0), ch, font=font)
        d.text(((128 - (r - l)) / 2 - l, (128 - (b - t_)) / 2 - t_), ch, font=font, fill=0)
        assert (np.asarray(im) < 128).any(), f"Noto has no glyph for {ch}"
        im.convert("RGB").save(p)
    return p


sys.argv = ["sample.py", f"--ckpt_dir={CK}", "--device=cuda:0",
            "--algorithm_type=dpmsolver++", "--guidance_type=classifier-free",
            "--guidance_scale=7.5", "--num_inference_steps=20", "--method=multistep"]
a = sample.arg_parse()
a.demo = False; a.save_image = False; a.save_image_dir = "/tmp/fd_cfg"; a.character_input = False
pipe = sample.load_fontdiffuer_pipeline(a)


def gen(ch):
    a.style_image_path = tgt(REF_CH)
    a.content_image_path = render_content(ch)
    img = sample.sampling(a, pipe)
    return None if img is None else img.convert("RGB").resize((CELL, CELL))


H = f"{OUT}/heldout"
os.makedirs(H, exist_ok=True)
for ch in heldout:
    (gen(ch) or Image.new("RGB", (CELL, CELL), "red")).save(f"{H}/{uname(ch)}.png")
print("heldout regenerated", len(heldout), flush=True)

G, S = f"{OUT}/glyphs", f"{OUT}/sheets"
os.makedirs(G, exist_ok=True); os.makedirs(S, exist_ok=True)
t0 = time.time(); failed = []; batch = []
for i, ch in enumerate(TODO):
    img = gen(ch)
    if img is None:
        failed.append(ch); img = Image.new("RGB", (CELL, CELL), "red")
    img.save(f"{G}/{uname(ch)}.png")
    batch.append((Image.open(render_content(ch)).convert("RGB").resize((CELL, CELL)), img))
    if len(batch) == 100 or i == len(TODO) - 1:
        n = len(batch); cols = 20; rows = (n + cols - 1) // cols
        sheet = Image.new("RGB", (CELL * cols, CELL * 2 * rows), "white")
        for j, (c, g) in enumerate(batch):
            x, y = (j % cols) * CELL, (j // cols) * 2 * CELL
            sheet.paste(c, (x, y)); sheet.paste(g, (x, y + CELL))
        d = ImageDraw.Draw(sheet)
        for r in range(rows):
            d.line([(0, r * 2 * CELL), (sheet.width, r * 2 * CELL)], fill="red", width=2)
        sheet.save(f"{S}/sheet_{i // 100:02d}.png")
        batch = []
        print(f"{i + 1}/{len(TODO)} done, {(time.time() - t0) / 60:.1f} min, failed {len(failed)}", flush=True)

with zipfile.ZipFile(f"{OUT}/glyphs_linzice_gen.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(glob.glob(f"{G}/*.png")):
        z.write(p, os.path.basename(p))
open(f"{OUT}/README.txt", "w", encoding="utf-8").write(
    "LinZiCe generated glyphs: 3500 level-1 minus his 263 real CJK = 3240 | N=100 ft 1000 steps from ckpt_ft | ref " + REF_CH +
    " | 20 steps | 96px" + NL + "failed (red): " + "".join(failed) + NL)
print("done", len(TODO), "failed", len(failed), f"{(time.time() - t0) / 60:.1f} min", flush=True)
