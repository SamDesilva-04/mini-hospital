"""Diet guide knowledge base. DRAFT content: every row needs sign-off by a qualified dietitian/doctor
before patient use. Set status='approved' and reviewed_by after review; set REQUIRE_APPROVED=1 in .env
to make the assistant use approved rows only."""
import os
import re

import db

SOURCE = "WHO healthy diet fact sheet (baseline). Disease-specific details: draft, clinical review required."

# key, everyday name, medical term, keywords, what it is, eat more, limit/avoid, tip, see a doctor urgently if
E = [
 ("diabetes", "high blood sugar condition", "diabetes mellitus", "diabetes,diabetic,sugar,glucose,hba1c,insulin",
  "The body cannot use sugar (glucose) properly, so it builds up in the blood.",
  "vegetables, lentils and beans, whole grains (oats, brown rice, millet), nuts, fish, fruit in small portions",
  "sugary drinks, sweets, large portions of white rice or bread, fried snacks",
  "Fill half the plate with vegetables and keep meal times regular.", "very high or very low sugar, confusion, vomiting"),
 ("prediabetes", "blood sugar higher than normal", "prediabetes", "prediabetes,borderline sugar",
  "Blood sugar is above normal but not yet in the diabetes range.",
  "vegetables, pulses, whole grains, nuts, fish, fruit in portions", "sugary drinks, sweets, refined flour foods, fried snacks",
  "Food changes plus regular activity can prevent it turning into diabetes.", "extreme thirst, frequent urination, unexplained weight loss"),
 ("hypertension", "high blood pressure", "hypertension", "hypertension,blood pressure,bp,salt",
  "The force of blood on the artery walls stays too high, which strains the heart and blood vessels.",
  "fruit, vegetables, pulses, whole grains, unsalted nuts, low-fat dairy, fish",
  "salt (aim under 5 g a day), pickles, processed meats, instant noodles, salty snacks",
  "Season with herbs, lemon and spices instead of salt, and check labels for sodium.", "severe headache, chest pain, vision changes"),
 ("cholesterol", "high blood fats", "dyslipidaemia (high cholesterol)", "cholesterol,lipid,triglyceride,ldl,dyslipidaemia",
  "Too much fat in the blood can slowly clog arteries.",
  "oats, beans, nuts, fish, vegetables, fruit, olive or sunflower oil",
  "butter, ghee, fatty meat, deep-fried food, bakery items with trans fats", "Swap saturated fats for unsaturated fats.", "chest pain, breathlessness"),
 ("obesity", "excess body weight", "obesity or overweight", "obesity,overweight,weight loss,bmi,lose weight",
  "Extra body fat raises the risk of diabetes, heart disease and joint problems.",
  "vegetables, pulses, whole grains, lean protein, water", "sugary drinks, fried snacks, sweets, very large portions",
  "Aim for slow, steady weight loss with regular meals and activity.", "chest pain, severe breathlessness"),
 ("chd", "narrowed heart arteries", "coronary heart disease", "heart disease,coronary,angina,heart attack,cardiac",
  "The arteries feeding the heart muscle become narrowed, reducing blood flow.",
  "fish, vegetables, fruit, whole grains, pulses, unsalted nuts", "salt, saturated fat, trans fat, processed meat, sugary foods",
  "A heart-healthy pattern works alongside your medicines.", "chest pain, pain spreading to the arm or jaw, sudden breathlessness"),
 ("heartfailure", "weak heart pump", "heart failure", "heart failure,swelling,fluid",
  "The heart cannot pump blood as well as the body needs.",
  "fresh vegetables, fruit, lean protein, whole grains", "salt, canned soups, pickles, processed food",
  "Weigh yourself daily and follow any fluid limit your doctor sets.", "fast weight gain, leg swelling, worsening breathlessness"),
 ("stroke", "brain blood-flow injury recovery", "stroke", "stroke,paralysis,brain attack",
  "Blood flow to part of the brain was blocked or a vessel bled.",
  "vegetables, fruit, whole grains, fish; softer or modified textures if swallowing is hard", "salt, saturated fat, sugary foods",
  "Ask for a swallowing check if eating or drinking causes coughing.", "sudden weakness, face drooping or speech trouble: call emergency services"),
 ("ckd", "long-term kidney damage", "chronic kidney disease", "kidney disease,ckd,renal,dialysis,creatinine",
  "The kidneys slowly lose their ability to filter waste from the blood.",
  "foods and portions set by your kidney dietitian", "salt; and, only if advised, high-potassium or high-phosphorus foods such as bananas, tomatoes, potatoes, colas",
  "Limits depend on your blood tests and stage, so do not restrict foods on your own.", "very little urine, swelling, shortness of breath"),
 ("kidneystones", "hard deposits in the kidney", "kidney stones (nephrolithiasis)", "kidney stone,stones,renal colic",
  "Minerals clump together into stones that can block urine flow.",
  "plenty of water, citrus fruit, vegetables, normal amounts of calcium-rich food", "salt, too much meat, sugary drinks; spinach and nuts if you have oxalate stones",
  "Drink enough that urine stays pale.", "severe side or back pain, fever, blood in urine"),
 ("gout", "painful joint swelling from uric acid", "gout", "gout,uric acid",
  "Uric acid crystals build up in a joint and cause sudden pain.",
  "water, vegetables, fruit, low-fat dairy, whole grains", "red meat, organ meats, shellfish, beer and spirits, sugary drinks",
  "Staying well hydrated helps flush uric acid.", "a hot, swollen joint with fever"),
 ("gerd", "acid coming up from the stomach", "gastro-oesophageal reflux disease (GERD)", "acid reflux,gerd,heartburn,acidity",
  "Stomach acid flows back into the food pipe and burns.",
  "oats, bananas, vegetables, lean protein, small meals", "fried and fatty food, very spicy food, citrus, coffee, chocolate, alcohol",
  "Stop eating 2 to 3 hours before bed.", "trouble swallowing, black stools, weight loss"),
 ("ulcer", "sore in the stomach lining", "peptic ulcer or gastritis", "ulcer,gastritis,stomach pain",
  "The stomach lining is inflamed or has a sore.",
  "regular small meals, vegetables, fruit, yoghurt, fibre", "alcohol, very spicy food, too much coffee; avoid smoking",
  "Do not skip meals.", "vomiting blood, black stools, severe pain"),
 ("ibs", "sensitive bowel", "irritable bowel syndrome (IBS)", "ibs,bloating,irritable bowel",
  "The gut becomes over-sensitive, causing cramps, bloating and changes in stools.",
  "regular meals, oats, water; a low-FODMAP trial only with a dietitian", "personal trigger foods, very fatty food, too much caffeine, sugar-free sweeteners",
  "Keep a food diary to spot your triggers.", "blood in stools, weight loss, night-time symptoms"),
 ("constipation", "hard or infrequent stools", "constipation", "constipation,hard stool",
  "Stools are hard, dry or passed less often than usual.",
  "vegetables, fruit, whole grains, pulses, plenty of water", "refined foods and low fluid intake",
  "Raise fibre slowly to avoid gas.", "blood in stools, severe pain, sudden change in habit"),
 ("diarrhoea", "loose watery stools", "acute diarrhoea", "diarrhoea,diarrhea,loose motion,loose stool",
  "Frequent watery stools, usually from an infection.",
  "oral rehydration solution, clear fluids, rice, banana, plain toast, soup", "greasy food, alcohol, sugary drinks",
  "Replacing fluids matters most.", "blood in stools, high fever, signs of dehydration, or lasting beyond 2 days (sooner for children and older adults)"),
 ("nafld", "fat built up in the liver", "non-alcoholic fatty liver disease", "fatty liver,nafld,liver",
  "Extra fat collects in liver cells, often linked to weight and sugar problems.",
  "vegetables, pulses, whole grains, fish, olive oil", "sugary drinks, sweets, fried food, refined carbohydrates, alcohol",
  "Gradual weight loss improves the liver.", "yellow skin or eyes, swollen belly"),
 ("gallstones", "stones in the gallbladder", "gallstones (cholelithiasis)", "gallstone,gallbladder",
  "Hard lumps form in the gallbladder and can block the bile duct.",
  "vegetables, fruit, whole grains, lean protein, smaller meals", "fatty and fried food; avoid crash diets",
  "Lose weight slowly, not rapidly.", "severe upper-right belly pain, fever, yellow skin"),
 ("anaemia", "low iron in the blood", "iron-deficiency anaemia", "anaemia,anemia,iron,haemoglobin,hemoglobin",
  "Too little iron means the blood carries less oxygen, causing tiredness.",
  "lentils, beans, green leafy vegetables, eggs, lean meat, with vitamin C foods (lemon, orange, guava)", "tea or coffee with meals, which reduce iron absorption",
  "Take iron tablets only as advised.", "fainting, chest pain, severe breathlessness"),
 ("osteoporosis", "weak, brittle bones", "osteoporosis", "osteoporosis,bone,calcium",
  "Bones lose density and break more easily.",
  "milk, yoghurt, ragi, small fish with bones, green leafy vegetables, protein foods", "too much salt, alcohol, cola drinks",
  "Sunlight and weight-bearing activity help bones.", "a fall with severe pain or a suspected fracture"),
 ("osteoarthritis", "joint wear and tear", "osteoarthritis", "arthritis,osteoarthritis,joint pain,knee pain",
  "The cartilage cushioning the joints gradually wears down.",
  "fruit, vegetables, fish, nuts, olive oil, whole grains", "sugary and heavily processed foods",
  "Keeping a healthy weight takes load off the joints.", "a hot, red, swollen joint with fever"),
 ("hypothyroid", "underactive thyroid", "hypothyroidism", "thyroid,hypothyroid,hypothyroidism",
  "The thyroid gland makes too little hormone, slowing the body down.",
  "balanced meals, iodized salt in normal amounts, eggs and fish", "large amounts of raw soy or cabbage-family foods",
  "Take the thyroid tablet on an empty stomach, apart from calcium or iron tablets.", "extreme tiredness, confusion, very slow heartbeat"),
 ("pcos", "hormone condition affecting the ovaries", "polycystic ovary syndrome (PCOS)", "pcos,pcod,polycystic",
  "Hormone imbalance causing irregular periods and often higher insulin levels.",
  "whole grains, pulses, vegetables, lean protein, nuts", "sugary foods and drinks, refined flour, fried food",
  "Weight control and activity can improve symptoms.", "very heavy bleeding, severe pelvic pain"),
 ("coeliac", "gut reaction to gluten", "coeliac disease", "coeliac,celiac,gluten",
  "Gluten damages the lining of the small intestine.",
  "naturally gluten-free foods: rice, maize, millet, potatoes, pulses, vegetables, fruit, meat, fish", "wheat, barley, rye and foods containing them; check labels for hidden gluten",
  "The gluten-free diet is lifelong and strict.", "severe belly pain, weight loss, persistent diarrhoea"),
 ("lactose", "trouble digesting milk sugar", "lactose intolerance", "lactose,milk intolerance",
  "The gut lacks the enzyme to break down lactose in milk.",
  "lactose-free milk, yoghurt or hard cheese in small amounts, calcium from ragi, greens and small fish", "large servings of milk and ice cream",
  "Keep calcium intake up from other foods.", "blood in stools, severe pain"),
 ("gdm", "high blood sugar in pregnancy", "gestational diabetes", "gestational,pregnancy sugar,pregnant diabetes",
  "Blood sugar rises during pregnancy and usually settles after birth.",
  "vegetables, pulses, whole grains, protein with each meal, small frequent meals", "sweets, fruit juice, large portions of white rice or bread",
  "Follow the plan from your obstetrician and dietitian.", "reduced baby movements, very high readings"),
 ("underweight", "not enough body weight or nutrition", "undernutrition", "underweight,malnutrition,weight gain,thin",
  "The body is not getting enough energy or nutrients.",
  "frequent energy-rich meals: milk, eggs, pulses, nuts, some oil or ghee, fruit", "skipping meals",
  "Eat small meals often and track your weight.", "rapid unexplained weight loss, persistent vomiting"),
 ("coldflu", "common cold and flu recovery", "viral respiratory infection", "cold,flu,cough,fever,influenza",
  "A virus infects the nose, throat and chest.",
  "fluids, soups, fruit, light easy-to-eat food", "alcohol and heavy greasy meals",
  "Rest and drink small amounts often.", "breathing difficulty, fever beyond 3 days, chest pain"),
 ("tb", "lung infection needing long treatment", "tuberculosis (TB)", "tuberculosis,tb",
  "A bacterial infection, mainly of the lungs, treated with months of medicines.",
  "extra energy and protein: pulses, eggs, milk, nuts, vegetables, fruit", "alcohol, which harms the liver alongside TB medicines",
  "Food supports recovery but never replaces the medicines.", "coughing blood, yellow skin, severe breathlessness"),
 ("migraine", "severe recurring headache", "migraine", "migraine,headache",
  "Repeated throbbing headaches, sometimes with nausea or light sensitivity.",
  "regular meals, plenty of water, magnesium foods (greens, nuts)", "your own triggers, such as alcohol, aged cheese, processed meats, too much caffeine; skipping meals",
  "A food diary shows which triggers are yours.", "sudden worst-ever headache, weakness, confusion"),
]

DDL = """CREATE TABLE IF NOT EXISTS diet_guides(
  key TEXT PRIMARY KEY, plain_name TEXT, medical_term TEXT, keywords TEXT, explanation TEXT,
  eat_more TEXT, limit_or_avoid TEXT, tip TEXT, urgent_signs TEXT,
  source TEXT, status TEXT DEFAULT 'draft', reviewed_by TEXT DEFAULT '')"""


def seed():
    db.write(DDL)
    if db.read("SELECT 1 FROM diet_guides LIMIT 1"):
        return
    for r in E:
        db.write("INSERT INTO diet_guides(key,plain_name,medical_term,keywords,explanation,eat_more,"
                 "limit_or_avoid,tip,urgent_signs,source) VALUES(?,?,?,?,?,?,?,?,?,?)", (*r, SOURCE))


def search(text, patient_keys=(), top=3):
    """Pick the guide rows that best match the question, plus the patient's own conditions."""
    words = set(re.findall(r"[a-z]+", text.lower()))
    rows = db.read("SELECT * FROM diet_guides" + (" WHERE status='approved'" if os.getenv("REQUIRE_APPROVED") == "1" else ""))
    scored = []
    for r in rows:
        score = sum(2 for k in r["keywords"].split(",") if k in words or (" " in k and k in text.lower()))
        score += 1 if r["key"] in patient_keys else 0
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:top]]


def as_prompt(rows):
    return "\n".join(
        f"- {r['plain_name']} ({r['medical_term']}) [status: {r['status']}]: {r['explanation']} "
        f"EAT MORE: {r['eat_more']}. LIMIT/AVOID: {r['limit_or_avoid']}. TIP: {r['tip']} "
        f"SEE A DOCTOR URGENTLY IF: {r['urgent_signs']}." for r in rows)
