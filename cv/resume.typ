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
#for p in data.publications.filter(p => p.featured) { publication(p, max: 5) }
#note[Full list: #link(data.site + "/publications", data.site.replace("https://", "") + "/publications")]

#section("Experience")
#entries(newest-first(keep(research(data)) + keep(industry(data))), short: true)

// Awards and teaching are left out of the 1-page resume with `resume: false`
// in cv.yaml (the EDIC Fellowship is already in the PhD entry); mentoring shows when filled.
#let others = keep(data.cv.awards) + keep(data.cv.at("mentoring", default: ())) + keep(data.cv.teaching)
#if others.len() > 0 {
  section(if keep(data.cv.at("mentoring", default: ())).len() > 0 { "Mentoring & Teaching" } else { "Awards & Teaching" })
  entries(others, short: true)
}

#section("Skills")
#skills(data.cv.skills)
