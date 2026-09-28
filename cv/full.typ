// Full CV (2 pages): every entry with details and all publications.
// Build: npm run cv   (reads dist/cv/data.json produced by the website build)
#import "template.typ": *

#let data = json(sys.inputs.at("data", default: "/dist/cv/data.json"))
#let phone = sys.inputs.at("phone", default: none)

#show: setup
#set document(title: "Emilien Seiler — Curriculum Vitae")
#set page(footer: context align(right, text(size: 8pt, fill: faint)[Emilien Seiler · #counter(page).display("1 / 1", both: true)]))
#header(data, phone: phone)
#summary(data)

#section("Education")
#entries(data.cv.education)

#let awards = data.cv.at("awards", default: ())
#if awards.len() > 0 {
  section("Fellowships & Awards")
  entries(awards)
}

#section("Publications")
#for p in data.publications { publication(p) }
#note[Also on #link(data.site + "/publications", data.site.replace("https://", "") + "/publications")]

#section("Experience")
#entries(newest-first(data.cv.experience))

#let mentoring = data.cv.at("mentoring", default: ())
#if mentoring.len() > 0 {
  section("Mentoring")
  entries(mentoring)
}

#section("Teaching")
#entries(data.cv.teaching)

#section("Skills")
#skills(data.cv.skills)
