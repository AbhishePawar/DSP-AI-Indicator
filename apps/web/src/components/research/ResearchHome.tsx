"use client";

import { FormEvent, useState } from "react";
import { ArrowRight, ChevronRight, Plus, Search } from "lucide-react";

const companies = [
  { symbol: "TCS", name: "Tata Consultancy Services" },
  { symbol: "HDFC Bank", name: "HDFC Bank Limited" },
  { symbol: "INFY", name: "Infosys Limited" },
  { symbol: "RELIANCE", name: "Reliance Industries" },
];

export function ResearchHome() {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState("Tata Consultancy Services");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (query.trim()) setSelected(query.trim());
  }

  return (
    <main className="min-h-screen bg-[#f5f1e8] text-[#122026]">
      <div className="flex min-h-screen">
        <aside className="hidden w-[29.5%] min-w-[300px] border-r border-[#d9d1c3] bg-[#fbfaf6] px-7 py-9 lg:block">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-serif text-[36px] font-semibold leading-none tracking-[-0.04em]">DSP</p>
              <p className="mt-4 text-[14px] font-medium uppercase tracking-[0.32em] text-[#55707a]">AI Research</p>
            </div>
            <ChevronRight className="mt-2 text-[#5b6b6b]" aria-hidden="true" />
          </div>

          <button className="mt-16 flex min-h-[70px] w-full items-center gap-4 rounded-[24px] border border-[#d9d1c3] px-7 text-[24px] text-[#10222a] transition-colors hover:bg-[#f3eee3]" type="button">
            <Plus aria-hidden="true" />
            Start New Research
          </button>

          <p className="mt-14 text-[16px] font-medium uppercase tracking-[0.26em] text-[#55707a]">Today</p>
          <nav className="mt-5 flex flex-col gap-1" aria-label="Recent research">
            {[
              "Tata Consultancy Services",
              "HDFC Bank Limited",
              "Infosys Limited",
            ].map((company, index) => (
              <button
                className={`rounded-[20px] px-5 py-4 text-left text-[23px] transition-colors ${index === 0 ? "bg-[#e9e1d2]" : "hover:bg-[#f3eee3]"}`}
                key={company}
                type="button"
                onClick={() => setSelected(company)}
              >
                {company}
              </button>
            ))}
          </nav>
        </aside>

        <section className="flex-1 px-5 py-16 sm:px-10 lg:px-20 lg:py-24">
          <div className="mx-auto max-w-[1240px]">
            <div className="text-center">
              <p className="text-[16px] font-semibold uppercase tracking-[0.34em] text-[#007d70]">DSP AI Research</p>
              <h1 className="mt-8 font-serif text-[52px] font-semibold leading-[0.98] tracking-[-0.045em] sm:text-[68px] lg:text-[78px]">Research any Indian company</h1>
              <p className="mx-auto mt-7 max-w-[720px] text-[22px] leading-[1.35] text-[#55707a]">DSP investigates the evidence, validates the data, and builds the investment case.</p>
            </div>

            <form onSubmit={submit} className="mt-16 rounded-[26px] border border-[#d7cdbd] bg-[#fffdf9] px-8 py-8 shadow-[0_2px_4px_rgba(70,55,30,0.04)]">
              <div className="flex items-center gap-5">
                <Search className="size-8 shrink-0 text-[#657575]" aria-hidden="true" />
                <input value={query} onChange={(event) => setQuery(event.target.value)} className="min-w-0 flex-1 bg-transparent text-[26px] outline-none placeholder:text-[#55707a]" placeholder="Search company, ticker or ISIN" aria-label="Search company, ticker or ISIN" />
              </div>
              <div className="mt-12 flex items-end justify-between gap-4">
                <p className="text-[18px] text-[#55707a]">Choose a security to confirm its identity before research begins.</p>
                <button className="inline-flex min-h-[64px] shrink-0 items-center gap-4 rounded-[22px] bg-[#91bdb1] px-7 text-[22px] font-medium text-white transition-colors hover:bg-[#76aa9d]" type="submit">Research <ArrowRight aria-hidden="true" /></button>
              </div>
            </form>

            <div className="mt-16 flex items-center justify-between gap-4">
              <p className="text-[16px] font-semibold uppercase tracking-[0.3em] text-[#55707a]">Suggested Research</p>
              <p className="text-[17px] text-[#55707a]">Start with a company</p>
            </div>
            <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {companies.map((company) => (
                <button className="rounded-[22px] border border-[#d7cdbd] bg-[#fffdf9] px-6 py-5 text-left transition-transform hover:-translate-y-0.5" key={company.symbol} type="button" onClick={() => setSelected(company.name)}>
                  <span className="block text-[22px] font-medium">{company.symbol}</span>
                  <span className="mt-2 block text-[18px] text-[#55707a]">{company.name}</span>
                </button>
              ))}
            </div>

            <button className="mt-5 flex w-full items-center justify-between rounded-[24px] border border-[#008875] bg-[#d5eee5] px-7 py-7 text-left transition-colors hover:bg-[#c7e8dc]" type="button">
              <span><span className="block text-[22px] font-semibold">DSP Indicator Analysis</span><span className="mt-3 block text-[18px] text-[#55707a]">Evaluate {selected || "a company"} using DSP&apos;s Buffett-style investment analysis framework.</span></span>
              <ArrowRight className="size-7 shrink-0 text-[#007d70]" aria-hidden="true" />
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}
