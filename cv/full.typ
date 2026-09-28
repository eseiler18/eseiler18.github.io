// Full CV (2 pages): every entry with details and all publications.
// Build: npm run cv   (reads dist/cv/data.json produced by the website build)
#import "template.typ": *

#let data = json(sys.inputs.at("data", default: "/dist/cv/data.json"))
#let phone = sys.inputs.at("phone", default: none)

#show: setup
#set document(title: "Emilien Seiler — Curriculum Vitae")
#set page(footer: context align(right, text(size: 8pt, fill: faint)[Emilien Seiler · #counter(page).display("1 / 1", both: true)]))
#header(data, phone: phone)

#row(text(size: 9pt, weight: 700, fill: soft, "Interests"), text(size: 9.2pt, data.profile.interests.join("  ·  ")))

#section("Education")
#entries(data.cv.education)

#section("Fellowships & Awards")
#entries(data.cv.awards)

#section("Publications")
#for p in data.publications { publication(p) }

#section("Research Experience")
#entries(research(data))

#section("Industry Experience")
#entries(industry(data))

#let mentoring = data.cv.at("mentoring", default: ())
#if mentoring.len() > 0 {
  section("Mentoring")
  entries(mentoring)
}

#section("Teaching")
#entries(data.cv.teaching)

#section("Skills")
#skills(data.cv.skills)
