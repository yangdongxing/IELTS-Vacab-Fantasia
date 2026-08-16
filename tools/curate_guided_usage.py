#!/usr/bin/env python3
"""Replace guided vocabulary templates with short, natural English examples."""

from __future__ import annotations

import argparse
import bz2
import json
import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import generate_spoken_usage as usage


ROOT = Path(__file__).resolve().parents[1]
SPOKEN_USAGE = ROOT / "data" / "spoken-usage.jsonl"
OUTPUT = ROOT / "data" / "guided-replacements.jsonl"
ENGLISH_CORPUS = Path("/private/tmp/eng_sentences_detailed.tsv.bz2")

BLOCKLIST = re.compile(
    r"\b(?:Tatoeba|Shtooka|Esperanto|Berber|Klingon|Tom|Mary|Sami|Mennad|Layla|Ziri|"
    r"Algeria|Algerian|Moscow|Trump|Hitler|God|Jesus|Quran|Bible|fuck|fucking|shit|"
    r"cock|dildo|sex|suicide|murder|kill|war|soldier|communist|proletarian)\b",
    re.I,
)
PROPER_NAME = re.compile(r"(?<![.!?]\s)\b[A-Z][a-z]{2,}\b")
DAILY_CUES = re.compile(
    r"\b(?:I|I'm|I've|I'd|we|we're|we've|you|your|please|today|tomorrow|yesterday|"
    r"work|home|school|shop|store|restaurant|hotel|train|bus|phone|file|doctor|"
    r"need|want|can|could|would|should|let's|how|what|where|when|why)\b",
    re.I,
)


FALLBACKS = {
    "alga": ("An alga can grow quickly in warm water.", "藻类在温暖的水中会快速生长。"),
    "biorhythm": ("My biorhythm changes whenever I work night shifts.", "每当我上夜班时，生物节律都会改变。"),
    "bush fire": ("The dry weather greatly increased the bush fire risk.", "干燥天气大大增加了林区火灾的风险。"),
    "cataclysmic": ("The earthquake caused cataclysmic damage across the region.", "地震给整个地区造成了灾难性的破坏。"),
    "chronology": ("The report presents a clear chronology of the events.", "报告清楚地按时间顺序列出了这些事件。"),
    "counterbalance": ("Regular exercise can counterbalance the effects of sitting all day.", "经常锻炼可以抵消久坐带来的影响。"),
    "decimation": ("The disease caused the decimation of the local population.", "这种疾病导致当地人口大幅减少。"),
    "despatch": ("We will despatch your order within two working days.", "我们会在两个工作日内发出你的订单。"),
    "destruct": ("The rocket is designed to destruct safely on command.", "这枚火箭被设计为按指令安全自毁。"),
    "ecliptic": ("The planets appear close to the ecliptic in the night sky.", "夜空中的行星看起来都靠近黄道。"),
    "ecologist": ("An ecologist studied how pollution affected the lake.", "一位生态学家研究了污染对湖泊的影响。"),
    "egalitarian": ("They want to build a more egalitarian society.", "他们希望建立一个更加平等的社会。"),
    "el nino": ("El Nino can disrupt weather patterns around the world.", "厄尔尼诺会扰乱全球的天气模式。"),
    "fieldwork": ("Our fieldwork begins early tomorrow morning.", "我们的实地考察明天一早开始。"),
    "fishery": ("The new rules aim to protect the local fishery.", "新规定旨在保护当地渔业。"),
    "fledgling": ("The fledgling company is already attracting new customers.", "这家初创公司已经开始吸引新客户。"),
    "flyby": ("The spacecraft completed a close flyby of the planet.", "航天器完成了一次近距离飞掠该行星的任务。"),
    "forage": ("The animals forage for food after sunset.", "这些动物在日落后觅食。"),
    "fulcrum": ("Place the fulcrum closer to the heavier end.", "把支点放得更靠近较重的一端。"),
    "gentry": ("The house once belonged to the local gentry.", "这栋房子过去属于当地乡绅。"),
    "germinate": ("These seeds need warmth and moisture to germinate.", "这些种子需要温度和水分才能发芽。"),
    "gorge": ("We followed a narrow path through the gorge.", "我们沿着一条狭窄的小路穿过峡谷。"),
    "headwater": ("The village lies near the headwaters of the river.", "这个村庄位于河流源头附近。"),
    "herbivore": ("A rabbit is a herbivore that mainly eats plants.", "兔子是主要以植物为食的草食动物。"),
    "horticulture": ("She studied horticulture before opening her garden center.", "她在开园艺中心前学习过园艺学。"),
    "hybridisation": ("Hybridisation can produce crops with useful new traits.", "杂交可以培育出具有实用新特性的作物。"),
    "hybridize": ("Farmers hybridize these plants to improve their yield.", "农民将这些植物杂交以提高产量。"),
    "hydraulic": ("The mechanic found a leak in the hydraulic system.", "机械师发现液压系统有泄漏。"),
    "hydrosphere": ("The hydrosphere includes all water found on Earth.", "水圈包括地球上的所有水体。"),
    "hygiene": ("Good hand hygiene helps prevent the spread of illness.", "良好的手部卫生有助于防止疾病传播。"),
    "invertebrate": ("An octopus is an invertebrate with remarkable intelligence.", "章鱼是一种非常聪明的无脊椎动物。"),
    "inductive": ("The teacher used inductive reasoning to explain the pattern.", "老师用归纳推理来解释这个规律。"),
    "irrigate": ("Farmers use this canal to irrigate their fields.", "农民用这条水渠灌溉农田。"),
    "jeopardise": ("A late payment could jeopardise the entire agreement.", "延迟付款可能会危及整个协议。"),
    "landform": ("Each landform was clearly marked on the map.", "每种地貌都清楚地标在地图上。"),
    "larva": ("The larva develops into an adult insect.", "幼虫会发育成成虫。"),
    "legume": ("Beans are an affordable legume rich in protein.", "豆类是一种价格实惠且富含蛋白质的豆科作物。"),
    "magma": ("Hot magma rose slowly beneath the volcano.", "炽热的岩浆在火山下方缓慢上升。"),
    "matriculation": ("You must submit these documents before matriculation.", "你必须在注册入学前提交这些文件。"),
    "maximal": ("The treatment produced a maximal response within an hour.", "治疗在一小时内产生了最大反应。"),
    "meltdown": ("The team worked quickly to prevent a system meltdown.", "团队迅速行动，防止系统彻底崩溃。"),
    "micro computer": ("This micro computer fits easily inside the device.", "这台微型计算机可以轻松装进设备内部。"),
    "monsoon": ("The monsoon usually brings heavy rain to the region.", "季风通常会给该地区带来强降雨。"),
    "numerate": ("Every employee needs to be confident and numerate.", "每位员工都需要自信并具备基本计算能力。"),
    "omnivore": ("Humans are omnivores who eat both plants and meat.", "人类是同时食用植物和肉类的杂食动物。"),
    "pedicab": ("We took a pedicab back to the hotel.", "我们坐人力三轮车回到了酒店。"),
    "pictograph": ("The pictograph shows how water use has changed.", "这张象形统计图显示了用水量的变化。"),
    "photosynthesis": ("Plants use sunlight to produce food through photosynthesis.", "植物通过光合作用利用阳光制造养分。"),
    "pollinate": ("Bees pollinate many of the crops we depend on.", "蜜蜂为许多我们赖以生存的农作物授粉。"),
    "postulate": ("The researchers postulate that stress affects sleep quality.", "研究人员推测压力会影响睡眠质量。"),
    "propel": ("A small motor propels the boat through the water.", "一台小型发动机推动船只在水中前进。"),
    "refraction": ("Refraction makes the straw look bent in the water.", "折射让水中的吸管看起来像弯了一样。"),
    "respire": ("Plants respire during both the day and the night.", "植物在白天和夜间都会呼吸。"),
    "scallion": ("Add some chopped scallion before serving the soup.", "上汤前加一些切碎的葱。"),
    "shade tolerant": ("This shade-tolerant plant grows well indoors.", "这种耐阴植物在室内长得很好。"),
    "short day": ("Rice is often described as a short-day plant.", "水稻通常被称为短日照植物。"),
    "slothful": ("A slothful routine can make you feel less energetic.", "懒散的生活习惯会让你感觉更没精神。"),
    "stemstalk": ("Cut the stemstalk just above the lowest leaf.", "在最下面的叶子上方剪断茎秆。"),
    "sterility": ("The doctor explained the possible causes of sterility.", "医生解释了不育的可能原因。"),
    "synthesise": ("The report synthesises findings from several recent studies.", "这份报告综合了几项近期研究的发现。"),
    "tributary": ("This small river is a tributary of the Amazon.", "这条小河是亚马孙河的一条支流。"),
    "watershed": ("The forest protects the watershed from soil erosion.", "这片森林保护流域免受水土流失。"),
}

# Human-reviewed replacements for corpus sentences with weak meaning, tone, or translation.
REVIEWED_OVERRIDES = {
    "acquisition": ("The acquisition will help our company enter new markets.", "这次收购将帮助公司进入新市场。"),
    "aggravate": ("Lack of sleep can aggravate your headache.", "睡眠不足会加重你的头痛。"),
    "agony": ("She was in agony after hurting her ankle.", "她脚踝受伤后疼痛难忍。"),
    "ancestor": ("One of my ancestors came from this village.", "我的一位祖先来自这个村庄。"),
    "anecdote": ("He shared a funny anecdote over dinner.", "他吃饭时讲了一件有趣的轶事。"),
    "artery": ("A blocked artery can cause serious health problems.", "动脉堵塞会引发严重的健康问题。"),
    "artifact": ("The museum displayed an ancient artifact behind glass.", "博物馆把一件古代文物陈列在玻璃柜中。"),
    "assert": ("You need to assert your rights calmly.", "你需要冷静地维护自己的权利。"),
    "audit": ("The company completed its annual audit last week.", "公司上周完成了年度审计。"),
    "augment": ("The new evidence may augment our understanding.", "新证据可能会增进我们的理解。"),
    "auxiliary": ("The hospital installed an auxiliary power system.", "医院安装了一套辅助供电系统。"),
    "backbone": ("Trust is the backbone of a strong team.", "信任是强大团队的支柱。"),
    "beak": ("The bird held a seed in its beak.", "那只鸟的喙里叼着一粒种子。"),
    "bewilder": ("The complicated instructions bewilder many new users.", "复杂的说明让许多新用户感到困惑。"),
    "bilateral": ("The two countries signed a bilateral trade agreement.", "两国签署了一项双边贸易协议。"),
    "binary": ("Computers store information using binary code.", "计算机使用二进制代码存储信息。"),
    "biography": ("I borrowed a biography of the famous scientist.", "我借了一本那位著名科学家的传记。"),
    "bombard": ("Please don't bombard me with questions right now.", "现在请不要连珠炮似地问我问题。"),
    "bond": ("Traveling together strengthened the bond between us.", "一起旅行加深了我们之间的感情。"),
    "burgeon": ("Online sales began to burgeon during the holiday season.", "节日期间网上销量开始迅速增长。"),
    "byproduct": ("Heat is a natural byproduct of this process.", "热量是这个过程的自然副产品。"),
    "calamity": ("Careful planning helped us avoid a greater calamity.", "周密计划帮助我们避免了更大的灾难。"),
    "camouflage": ("The jacket provides good camouflage in the forest.", "这件夹克在森林中有很好的伪装效果。"),
    "catalyst": ("Her suggestion became a catalyst for positive change.", "她的建议成了积极改变的催化剂。"),
    "checklist": ("I use a checklist before every business trip.", "每次出差前我都会使用清单。"),
    "clap": ("Everyone began to clap after the performance.", "表演结束后大家开始鼓掌。"),
    "cloak": ("She wore a warm cloak over her dress.", "她在连衣裙外披了一件暖和的斗篷。"),
    "clone": ("Scientists can clone plants from a single cell.", "科学家可以用单个细胞克隆植物。"),
    "collide": ("Two bicycles collided at the busy intersection.", "两辆自行车在繁忙的路口相撞了。"),
    "collision": ("The driver narrowly avoided a collision.", "司机勉强避免了一次碰撞。"),
    "commander": ("The rescue commander coordinated the entire operation.", "救援指挥官协调了整个行动。"),
    "commentary": ("The match commentary was clear and engaging.", "这场比赛的解说清楚又有吸引力。"),
    "commercial": ("The building is intended for commercial use.", "这栋建筑用于商业用途。"),
    "condense": ("Please condense the report into one page.", "请把报告精简到一页。"),
    "coordinate": ("We need to coordinate our schedules first.", "我们需要先协调各自的时间安排。"),
    "constraint": ("Time is our biggest constraint right now.", "时间是我们目前最大的限制。"),
    "contend": ("Several teams will contend for the championship.", "几支队伍将争夺冠军。"),
    "contention": ("The budget remains a point of contention.", "预算仍然是争议的焦点。"),
    "counterfeit": ("The cashier noticed that the note was counterfeit.", "收银员发现那张钞票是假的。"),
    "criteria": ("Price and quality are our main criteria.", "价格和质量是我们的主要标准。"),
    "curative": ("This herb is believed to have curative properties.", "人们认为这种草药具有治疗作用。"),
    "daring": ("It was a daring plan, but it worked.", "这是个大胆的计划，但成功了。"),
    "decompose": ("Food waste will decompose faster in warm conditions.", "厨余垃圾在温暖环境中分解得更快。"),
    "deduce": ("We can deduce the answer from these clues.", "我们可以从这些线索推断出答案。"),
    "deem": ("The building was deemed unsafe after inspection.", "检查后，这栋建筑被认定为不安全。"),
    "default": ("The app uses this setting by default.", "这个应用默认使用这项设置。"),
    "defer": ("Can we defer the decision until Monday?", "我们可以把决定推迟到周一吗？"),
    "deficit": ("The company is working to reduce its budget deficit.", "公司正在努力减少预算赤字。"),
    "delta": ("The river forms a wide delta near the coast.", "这条河在海岸附近形成了宽阔的三角洲。"),
    "depict": ("The painting depicts a busy street market.", "这幅画描绘了一个繁忙的街头市场。"),
    "descendant": ("She is a descendant of the original owner.", "她是原主人的后代。"),
    "desolate": ("The beach looked desolate during the winter.", "冬天的海滩看起来十分荒凉。"),
    "deter": ("Security cameras may deter people from stealing.", "监控摄像头可能会阻止人们偷窃。"),
    "diagnose": ("The doctor diagnosed me with a mild infection.", "医生诊断我患有轻微感染。"),
    "dictate": ("Urgent needs may dictate a change of plan.", "紧急需求可能会迫使我们改变计划。"),
    "dimension": ("Please check the dimension before ordering the shelf.", "订购架子前请核对尺寸。"),
    "displace": ("The new sofa will displace the old one.", "新沙发将取代旧沙发。"),
    "doctrine": ("The course examines economic doctrine and public policy.", "这门课程研究经济学说和公共政策。"),
    "downsize": ("We decided to downsize to a smaller apartment.", "我们决定换到一套更小的公寓。"),
    "dramatic": ("There has been a dramatic improvement in service.", "服务有了显著改善。"),
    "dwelling": ("The old dwelling has been carefully restored.", "这座旧住所得到了精心修复。"),
    "dwindle": ("Our savings began to dwindle after the move.", "搬家后我们的积蓄开始减少。"),
    "dynamics": ("The new manager changed the team dynamics.", "新经理改变了团队的互动方式。"),
    "dysfunction": ("Poor communication can cause team dysfunction.", "沟通不畅会导致团队运作失调。"),
    "elegance": ("I admire the simplicity and elegance of this design.", "我很欣赏这个设计的简洁与优雅。"),
    "embellish": ("You don't need to embellish the story.", "你不必对这个故事添油加醋。"),
    "eminent": ("An eminent specialist reviewed my test results.", "一位杰出的专家查看了我的检查结果。"),
    "enhance": ("This update should enhance the user experience.", "这次更新应该会改善用户体验。"),
    "enlighten": ("Could you enlighten me about the new policy?", "你能给我讲讲这项新政策吗？"),
    "enterprise": ("She started a small catering enterprise from home.", "她在家创办了一家小型餐饮企业。"),
    "entity": ("The two branches operate as one legal entity.", "这两个分支作为同一个法律实体运营。"),
    "equip": ("The course will equip you with practical skills.", "这门课程会让你掌握实用技能。"),
    "equity": ("The company offered employees a share of its equity.", "公司向员工提供了一部分股权。"),
    "excavate": ("Workers began to excavate the site this morning.", "工人们今天早上开始挖掘现场。"),
    "excrete": ("The kidneys filter blood and excrete waste.", "肾脏过滤血液并排出废物。"),
    "exhale": ("Breathe in slowly, then exhale through your mouth.", "慢慢吸气，然后用嘴呼气。"),
    "expanse": ("A vast expanse of water lay ahead.", "前方是一片辽阔的水域。"),
    "expel": ("The fan helps expel hot air outside.", "风扇有助于把热空气排到室外。"),
    "exponent": ("She is a leading exponent of sustainable design.", "她是可持续设计的主要倡导者。"),
    "exterior": ("The exterior of the house needs repainting.", "房子的外墙需要重新粉刷。"),
    "exterminate": ("The treatment should exterminate the harmful pests.", "这种处理应该能消灭有害虫害。"),
    "facility": ("The new sports facility opens next month.", "新的体育设施下个月开放。"),
    "faculty": ("She joined the engineering faculty last year.", "她去年加入了工程学院。"),
    "fatigue": ("Long working hours can lead to fatigue.", "长时间工作会导致疲劳。"),
    "fauna": ("The island has a rich variety of fauna.", "这座岛拥有丰富多样的动物群。"),
    "fellowship": ("The program offers a research fellowship abroad.", "这个项目提供海外研究奖学金。"),
    "fertilize": ("We fertilize the garden twice a year.", "我们每年给花园施肥两次。"),
    "feudalism": ("The course explains how feudalism shaped medieval society.", "这门课程解释封建制度如何塑造中世纪社会。"),
    "flare": ("The pain may flare after intense exercise.", "剧烈运动后疼痛可能会突然加重。"),
    "fleet": ("The company is replacing its delivery fleet.", "公司正在更换配送车队。"),
    "flora": ("The region is known for its diverse flora.", "这个地区以多样的植物群而闻名。"),
    "fume": ("Please open a window to release the fumes.", "请打开窗户让烟气散出去。"),
    "functional": ("The kitchen is small but highly functional.", "这个厨房虽小但非常实用。"),
    "fungus": ("A fungus is growing on the damp wall.", "潮湿的墙上长出了一种真菌。"),
    "fuss": ("Don't make a fuss about a small mistake.", "不要为一个小错误大惊小怪。"),
    "generator": ("The generator kept the lights on overnight.", "发电机让灯整晚都亮着。"),
    "gizmo": ("This handy gizmo can charge three devices.", "这个方便的小装置可以给三台设备充电。"),
    "gland": ("This gland produces hormones that control growth.", "这个腺体产生控制生长的激素。"),
    "gourmet": ("The shop sells gourmet cheese and fresh bread.", "这家店出售精品奶酪和新鲜面包。"),
    "grid": ("The storm caused a failure across the power grid.", "暴风雨导致整个电网发生故障。"),
    "grind": ("Can you grind these coffee beans for me?", "你能帮我磨一下这些咖啡豆吗？"),
    "hallowed": ("The university hall is a hallowed place for graduates.", "这座大学礼堂是毕业生心中的圣地。"),
    "hasten": ("This shortcut may hasten the approval process.", "这条捷径可能会加快审批流程。"),
    "hay": ("The farmer stored the hay in a barn.", "农民把干草储存在谷仓里。"),
    "hazard": ("Loose cables are a serious safety hazard.", "松散的电线是严重的安全隐患。"),
    "hibernation": ("The bear enters hibernation during the winter.", "熊在冬季进入冬眠。"),
    "hierarchy": ("The company has a clear management hierarchy.", "公司有明确的管理层级。"),
    "hijack": ("Attackers tried to hijack his online account.", "攻击者试图劫持他的网络账户。"),
    "hostile": ("The customer became hostile during the conversation.", "那位顾客在交谈中变得很不友好。"),
    "housewife": ("The housewife runs a successful online store.", "这位家庭主妇经营着一家成功的网店。"),
    "hull": ("The boat's hull needs urgent repairs.", "船体急需维修。"),
    "icon": ("Tap the blue icon to open settings.", "点击蓝色图标打开设置。"),
    "illiteracy": ("The program aims to reduce adult illiteracy.", "这个项目旨在减少成年人文盲现象。"),
    "increment": ("The salary increases by a small increment each year.", "工资每年都会小幅增加。"),
    "induce": ("The medicine may induce sleep within an hour.", "这种药可能会在一小时内引起睡意。"),
    "inflection": ("Her rising inflection made the statement sound like a question.", "她上扬的语调让陈述听起来像疑问句。"),
    "influx": ("The town expects an influx of visitors this weekend.", "小镇预计本周末会迎来大量游客。"),
    "instance": ("This is one instance where the rule applies.", "这是该规则适用的一个例子。"),
    "interbreed": ("These two varieties can interbreed successfully.", "这两个品种可以成功杂交。"),
    "interstellar": ("The spacecraft is beginning its interstellar journey.", "这艘航天器正开始星际旅程。"),
    "intestine": ("The intestine absorbs nutrients from digested food.", "肠道从消化后的食物中吸收营养。"),
    "intonation": ("Your intonation sounds more natural now.", "你的语调现在听起来更自然了。"),
    "invoice": ("Please email the invoice to our accounts team.", "请把发票通过邮件发给财务团队。"),
}

FALLBACKS.update(REVIEWED_OVERRIDES)

REVIEWED_OVERRIDES_2 = {
    "jade": ("She chose a simple jade bracelet.", "她选了一只简约的玉手镯。"),
    "kidney": ("The kidneys remove waste from your blood.", "肾脏会清除血液中的废物。"),
    "lament": ("Many residents lament the loss of the old park.", "许多居民对老公园的消失感到惋惜。"),
    "lay off": ("The company may lay off some temporary staff.", "公司可能会裁掉一些临时员工。"),
    "lethal": ("Even a small dose can be lethal.", "即使很小的剂量也可能致命。"),
    "liberal": ("The school has a liberal approach to dress codes.", "学校对着装规定采取宽松态度。"),
    "limb": ("He injured a lower limb while hiking.", "他徒步时伤到了一条下肢。"),
    "literate": ("Most jobs require people to be digitally literate.", "大多数工作要求人们具备数字素养。"),
    "locomotive": ("The old steam locomotive is still running.", "那台老式蒸汽机车仍在运行。"),
    "manifest": ("The problem may manifest in several different ways.", "这个问题可能以几种不同方式表现出来。"),
    "mantle": ("Snow formed a white mantle over the hills.", "白雪像一层外衣覆盖着群山。"),
    "maritime": ("The city has a long maritime history.", "这座城市有着悠久的海事历史。"),
    "mason": ("A skilled mason repaired the stone wall.", "一位熟练的石匠修好了石墙。"),
    "masquerade": ("The party was organized as a masquerade.", "这场派对以化装舞会的形式举办。"),
    "meantime": ("The repair will take an hour; wait here in the meantime.", "维修需要一小时，在此期间请在这里等候。"),
    "mill": ("The old mill now produces organic flour.", "这座老磨坊现在生产有机面粉。"),
    "mint": ("Add a few fresh mint leaves to the drink.", "在饮料里加几片新鲜薄荷叶。"),
    "mistress": ("The mistress of the house welcomed every guest.", "这家的女主人欢迎了每位客人。"),
    "moan": ("Try not to moan about every small delay.", "尽量不要为每次小延误都抱怨。"),
    "mold": ("You can mold the clay into any shape.", "你可以把黏土塑成任何形状。"),
    "mortgage": ("We're applying for a mortgage to buy the apartment.", "我们正在申请房贷购买这套公寓。"),
    "morphine": ("The doctor explained why morphine was necessary.", "医生解释了为什么需要使用吗啡。"),
    "muffle": ("The thick curtains help muffle street noise.", "厚窗帘有助于减弱街道噪音。"),
    "naval": ("The museum has an exhibition on naval history.", "博物馆有一个海军历史展览。"),
    "nobility": ("The novel describes the lives of the local nobility.", "这本小说描写了当地贵族的生活。"),
    "opt": ("I decided to opt for the cheaper plan.", "我决定选择更便宜的方案。"),
    "optics": ("This course introduces the basic principles of optics.", "这门课程介绍光学的基本原理。"),
    "organism": ("Every living organism needs water to survive.", "每个生物体都需要水才能生存。"),
    "oversee": ("She will oversee the project from start to finish.", "她将全程监督这个项目。"),
    "overwhelming": ("The amount of information can feel overwhelming.", "信息量太大时会让人难以承受。"),
    "overwork": ("Constant overwork can damage your health.", "长期过度工作会损害健康。"),
    "oxide": ("The metal surface was covered with oxide.", "金属表面覆盖着氧化物。"),
    "parameter": ("You can adjust each parameter in the settings.", "你可以在设置中调整每个参数。"),
    "paste": ("Mix the flour and water into a smooth paste.", "把面粉和水混合成光滑的糊状物。"),
    "patrol": ("Security guards patrol the building at night.", "保安夜间会在大楼里巡逻。"),
    "pedal": ("Press the brake pedal gently when slowing down.", "减速时轻踩刹车踏板。"),
    "peril": ("The hikers were unaware of the peril ahead.", "徒步者没有意识到前方的危险。"),
    "peripheral": ("The printer is a useful computer peripheral.", "打印机是一种实用的计算机外设。"),
    "pest": ("This spray keeps garden pests away.", "这种喷雾可以驱除花园害虫。"),
    "petition": ("Residents signed a petition to save the library.", "居民签署请愿书，希望保住图书馆。"),
    "pivot": ("Customer feedback became the pivot of our new strategy.", "客户反馈成了我们新策略的关键。"),
    "plantation": ("The old tea plantation is open to visitors.", "这座老茶园向游客开放。"),
    "plumb": ("A professional will plumb the new bathroom tomorrow.", "专业人员明天会为新浴室安装水管。"),
    "plume": ("A dark plume of smoke rose above the building.", "一股黑烟升到大楼上方。"),
    "pollutant": ("The filter removes harmful pollutants from the water.", "过滤器会去除水中的有害污染物。"),
    "potent": ("This is a potent medicine, so follow the instructions.", "这是一种药效很强的药，请按说明服用。"),
    "predator": ("The owl is an effective nighttime predator.", "猫头鹰是一种高效的夜间捕食者。"),
    "prefix": ("Add the prefix un- to make the opposite meaning.", "加上前缀 un- 可以表达相反的意思。"),
    "primate": ("The sanctuary cares for several endangered primates.", "保护区照料着几种濒危灵长类动物。"),
    "proclaim": ("The sign proclaims that the shop is open.", "招牌清楚地写着商店正在营业。"),
    "proponent": ("She is a strong proponent of flexible working.", "她是弹性工作的坚定支持者。"),
    "prophet": ("The novel tells the story of an ancient prophet.", "这本小说讲述了一位古代先知的故事。"),
    "protocol": ("Please follow the safety protocol in the laboratory.", "请遵守实验室的安全规程。"),
    "purify": ("This filter can purify drinking water.", "这个过滤器可以净化饮用水。"),
    "quadruple": ("Online orders quadrupled during the holiday sale.", "节日促销期间网上订单增加到四倍。"),
    "quarterly": ("We review our budget on a quarterly basis.", "我们每季度审核一次预算。"),
    "rack": ("Hang your coat on the rack by the door.", "把外套挂在门边的衣架上。"),
    "radiate": ("The heater will radiate warmth across the room.", "加热器会向整个房间散发热量。"),
    "radioactive": ("Radioactive material must be stored safely.", "放射性材料必须安全存放。"),
    "raid": ("Police conducted a raid on the illegal warehouse.", "警方突击搜查了非法仓库。"),
    "reclaim": ("The project aims to reclaim polluted land.", "这个项目旨在治理并重新利用受污染的土地。"),
    "recruit": ("The company plans to recruit more engineers.", "公司计划招聘更多工程师。"),
    "reel": ("The fisherman pulled in the reel slowly.", "渔夫慢慢收起卷线轮。"),
    "reproduce": ("The printer can reproduce photos accurately.", "这台打印机可以准确复制照片。"),
    "respondent": ("Each respondent answered the same ten questions.", "每位受访者都回答了相同的十个问题。"),
    "rotate": ("Rotate the screen to view the image horizontally.", "旋转屏幕以横向查看图片。"),
    "rudimentary": ("I only have a rudimentary knowledge of coding.", "我只掌握一些基础编程知识。"),
    "safeguard": ("Strong passwords safeguard your personal information.", "强密码可以保护你的个人信息。"),
    "saturate": ("Heavy rain quickly saturated the dry soil.", "大雨很快浸透了干燥的土壤。"),
    "saucer": ("She placed the cup back on its saucer.", "她把杯子放回茶碟上。"),
    "scrutinise": ("Please scrutinise the contract before signing it.", "签字前请仔细审查合同。"),
    "sculpture": ("A modern sculpture stands outside the library.", "图书馆外立着一座现代雕塑。"),
    "seaman": ("The experienced seaman checked the weather forecast.", "那位经验丰富的海员查看了天气预报。"),
    "segregate": ("The facility segregates recyclable waste from general rubbish.", "该设施把可回收垃圾与普通垃圾分开。"),
    "semantic": ("The two phrases have a subtle semantic difference.", "这两个短语在语义上有细微差别。"),
    "senate": ("The senate approved the new education budget.", "参议院批准了新的教育预算。"),
    "siege": ("The castle survived a long siege.", "这座城堡经受住了长期围困。"),
    "simulate": ("The software can simulate different weather conditions.", "这个软件可以模拟不同的天气条件。"),
    "skim": ("I usually skim the news before breakfast.", "我通常在早餐前快速浏览新闻。"),
    "slender": ("The lamp has a slender metal frame.", "这盏灯有一个纤细的金属框架。"),
    "socialism": ("The lecture compares capitalism with socialism.", "这场讲座比较资本主义与社会主义。"),
    "spectrum": ("The symptoms cover a broad spectrum.", "这些症状涉及很广的范围。"),
    "stature": ("She is small in stature but very strong.", "她身材娇小，但非常强壮。"),
    "steward": ("The flight steward helped us find our seats.", "乘务员帮助我们找到了座位。"),
    "stigma": ("We need to reduce the stigma around mental health.", "我们需要减少人们对心理健康问题的偏见。"),
    "stipulate": ("The contract stipulates a thirty-day notice period.", "合同规定需要提前三十天通知。"),
    "strangle": ("Tight weeds can strangle young garden plants.", "缠绕过紧的杂草会妨碍幼苗生长。"),
    "strive": ("We strive to provide better customer service.", "我们努力提供更好的客户服务。"),
    "succession": ("Three meetings took place in quick succession.", "三场会议接连举行。"),
    "sustainable": ("We need a sustainable solution to this problem.", "我们需要一个可持续的问题解决方案。"),
    "takeaway": ("The main takeaway is to start planning early.", "主要启示是要尽早开始计划。"),
    "thorough": ("The mechanic performed a thorough safety check.", "机械师进行了彻底的安全检查。"),
    "tornado": ("The tornado damaged several homes near the town.", "龙卷风损坏了小镇附近的几所房屋。"),
    "transparent": ("The company should be transparent about its fees.", "公司应该公开透明地说明收费。"),
    "trauma": ("She is receiving support after the trauma.", "创伤发生后，她正在接受支持和帮助。"),
    "trench": ("Workers dug a trench along the road.", "工人们沿着道路挖了一条沟。"),
    "trespass": ("Do not trespass on private property.", "请勿擅自进入私人领地。"),
    "turnip": ("I added a chopped turnip to the soup.", "我在汤里加了切碎的芜菁。"),
    "uptake": ("The uptake of the new service has been slow.", "这项新服务的采用速度一直较慢。"),
    "usage": ("Check the label for correct usage instructions.", "请查看标签上的正确使用说明。"),
    "vault": ("The documents are stored in a secure vault.", "这些文件存放在安全的保险库里。"),
    "vegetation": ("Dense vegetation covered both sides of the path.", "茂密的植被覆盖着小路两侧。"),
    "veil": ("She wore a light veil over her face.", "她脸上蒙着一层轻薄的面纱。"),
    "volt": ("The battery provides twelve volts of power.", "这块电池提供十二伏电压。"),
    "wasabi": ("Would you like some wasabi with your sushi?", "你的寿司需要配一些芥末吗？"),
    "wax": ("Use this wax to protect the wooden table.", "用这种蜡保护木桌。"),
    "wedge": ("Put a small wedge under the door.", "在门下面放一个小楔子。"),
    "well being": ("Regular breaks are important for your well-being.", "定期休息对你的身心健康很重要。"),
    "wholesale": ("We buy these products at wholesale prices.", "我们以批发价购买这些产品。"),
    "womb": ("A baby develops inside the womb.", "婴儿在子宫内发育。"),
    "workforce": ("The company has a diverse international workforce.", "公司拥有多元化的国际员工队伍。"),
}

FALLBACKS.update(REVIEWED_OVERRIDES_2)


def load_targets() -> list[dict[str, object]]:
    rows = [
        json.loads(line)
        for line in SPOKEN_USAGE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if OUTPUT.exists():
        replacement_keys = [
            str(json.loads(line)["key"])
            for line in OUTPUT.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        rows_by_key = {str(row["key"]): row for row in rows}
        return [rows_by_key[item_key] for item_key in replacement_keys]
    return [row for row in rows if row.get("source") == "guided"]


def sentence_score(sentence: str, target: str) -> tuple[int, str]:
    words = usage.english_words(sentence)
    score = abs(len(words) - 7) * 4 + len(sentence) // 50
    if DAILY_CUES.search(sentence):
        score -= 8
    if sentence.rstrip().endswith("?"):
        score -= 2
    if target in {word.lower() for word in words}:
        score -= 3
    score += len(PROPER_NAME.findall(sentence)) * 12
    score += len(re.findall(r"[,;:]", sentence)) * 2
    if re.search(r"[\"“”]|\.{3}|\(|\)|\d{4}|\b(?:thus|thereof|whereby|henceforth|whilst)\b", sentence, re.I):
        score += 10
    return score, sentence


def collect_candidates(targets: list[str]) -> dict[str, list[dict[str, str]]]:
    forms_by_token: dict[str, set[str]] = defaultdict(set)
    phrases: dict[str, re.Pattern[str]] = {}
    for target in targets:
        if " " in target:
            phrases[target] = usage.phrase_pattern(target)
        else:
            for form in usage.target_forms(target):
                forms_by_token[form].add(target)

    candidates: dict[str, list[dict[str, str]]] = defaultdict(list)
    with bz2.open(ENGLISH_CORPUS, "rt", encoding="utf-8") as stream:
        for line in stream:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            sentence = parts[2].strip()
            words = usage.english_words(sentence)
            if not 3 <= len(words) <= 12 or BLOCKLIST.search(sentence):
                continue
            matches: set[str] = set()
            for token in {word.lower() for word in words}:
                matches.update(forms_by_token.get(token, ()))
            for target, pattern in phrases.items():
                if pattern.search(sentence):
                    matches.add(target)
            for target in matches:
                if usage.sentence_has_target(sentence, target):
                    candidates[target].append({
                        "en": sentence,
                        "attribution": f"CC BY 2.0 FR: Tatoeba #{parts[0]} ({parts[3].strip() or 'unknown'})",
                    })
    return candidates


def translate_batch(sentences: list[str]) -> list[str]:
    command = [
        "curl", "-fsS", "--retry", "3", "--retry-delay", "1", "--get",
        "https://translate.googleapis.com/translate_a/single",
        "--data-urlencode", "client=gtx",
        "--data-urlencode", "sl=en",
        "--data-urlencode", "tl=zh-CN",
        "--data-urlencode", "dt=t",
        "--data-urlencode", f"q={'\n'.join(sentences)}",
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    payload = json.loads(result.stdout)
    translated = "".join(part[0] for part in payload[0] if part[0]).splitlines()
    if len(translated) != len(sentences):
        raise RuntimeError(f"translation count mismatch: {len(translated)} != {len(sentences)}")
    return translated


def simplify_chinese(records: list[dict[str, str]]) -> None:
    wrapper = [{"zh": record["zh"]} for record in records]
    usage.simplify_chinese_batch(wrapper)
    for record, converted in zip(records, wrapper):
        record["zh"] = str(converted["zh"])


def build() -> list[dict[str, str]]:
    target_rows = load_targets()
    targets = [str(row["key"]) for row in target_rows]
    candidates = collect_candidates(targets)
    selected: list[dict[str, str]] = []
    for row in target_rows:
        target = str(row["key"])
        if target in FALLBACKS:
            english, chinese = FALLBACKS[target]
            selected.append({"key": target, "en": english, "zh": chinese, "source": "curated"})
            continue
        options = sorted(candidates.get(target, ()), key=lambda item: sentence_score(item["en"], target))
        if not options:
            raise RuntimeError(f"no replacement candidate or fallback for {target}")
        choice = options[0]
        selected.append({
            "key": target,
            "en": choice["en"],
            "zh": "",
            "source": "curated-corpus",
            "attribution": choice["attribution"],
        })

    pending = [record for record in selected if not record["zh"]]
    for start in range(0, len(pending), 40):
        batch = pending[start:start + 40]
        translations = translate_batch([record["en"] for record in batch])
        for record, chinese in zip(batch, translations):
            record["zh"] = re.sub(r"\s*[/／]+\s*", "或", chinese.strip())
        time.sleep(0.1)
    simplify_chinese(selected)
    return selected


def validate(records: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    targets = [str(row["key"]) for row in load_targets()]
    keys = [record.get("key", "") for record in records]
    if keys != targets:
        errors.append("replacement keys do not exactly match the guided baseline")
    for record in records:
        target, english, chinese = record["key"], record["en"], record["zh"]
        if not usage.sentence_has_target(english, target):
            errors.append(f"target missing: {target}: {english}")
        if not 3 <= len(usage.english_words(english)) <= 12:
            errors.append(f"invalid length: {target}: {english}")
        if BLOCKLIST.search(english):
            errors.append(f"blocked content: {target}: {english}")
        if not re.search(r"[\u3400-\u9fff]", chinese):
            errors.append(f"missing Chinese: {target}")
        if re.search(r"[/／]", chinese):
            errors.append(f"spoken slash: {target}: {chinese}")
        if english.lower().startswith("a useful example is"):
            errors.append(f"example prefix: {target}")
    return errors


def write(records: list[dict[str, str]]) -> None:
    text = "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records)
    OUTPUT.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "validate"))
    args = parser.parse_args()
    records = build() if args.command == "build" else [
        json.loads(line) for line in OUTPUT.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    errors = validate(records)
    if not errors and args.command == "build":
        write(records)
    print(f"Records: {len(records)}; validation: {len(errors)} issue(s)")
    for error in errors[:100]:
        print("-", error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
