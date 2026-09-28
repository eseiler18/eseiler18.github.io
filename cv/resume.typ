// 1-page resume for research internship applications.
// Build: npm run cv   (reads dist/cv/data.json produced by the website build)
#import "template.typ": *

#let data = json(sys.inputs.at("data", default: "/dist/cv/data.json"))
#let phone = sys.inputs.at("phone", default: none)
#let keep(list) = list.filter(e => e.at("resume", default: true))

#show: setup
#set document(title: "Emilien Seiler — Resume")
#header(data, phone: phone)

#section("Education")
#entries(keep(data.cv.education), short: true)

#section("Publications")
#for (i, p) in data.publications.filter(p => p.featured).enumerate() { publication(p, i + 1) }
#text(size: 9pt, fill: soft)[Full list: #link(data.site + "/publications", data.site.replace("https://", "") + "/publications")]

#section("Research Experience")
#entries(keep(research(data)), short: true)

#section("Industry Experience")
#entries(keep(industry(data)), short: true)

#let mentoring = keep(data.cv.at("mentoring", default: ()))
#section(if mentoring.len() > 0 { "Awards, Mentoring & Teaching" } else { "Awards & Teaching" })
#entries(keep(data.cv.awards), short: true)
#entries(mentoring, short: true)
#entries(keep(data.cv.teaching), short: true)

#section("Skills")
#skills(data.cv.skills)
