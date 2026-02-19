export default function DemoScholarshipForm() {
  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10 text-slate-900">
      <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold">International Scholarship Application</h1>
        <p className="mt-2 text-sm text-slate-600">
          Demo form used by Service Agent automation. Fields here are intentionally straightforward for reliable browser control.
        </p>

        <form className="mt-6 space-y-4">
          <label className="block">
            <span className="text-sm font-semibold text-slate-700">Legal Name</span>
            <input
              name="legal_name"
              type="text"
              placeholder="Full name as shown on passport"
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700">Date of Birth</span>
            <input name="date_of_birth" type="date" className="mt-1 w-full rounded-lg border border-slate-300 p-2" />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700">Passport Number</span>
            <input name="passport_number" type="text" className="mt-1 w-full rounded-lg border border-slate-300 p-2" />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700">Email</span>
            <input name="email" type="email" className="mt-1 w-full rounded-lg border border-slate-300 p-2" />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700">Nationality</span>
            <input name="nationality" type="text" className="mt-1 w-full rounded-lg border border-slate-300 p-2" />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700">Intended Program</span>
            <input name="intended_program" type="text" className="mt-1 w-full rounded-lg border border-slate-300 p-2" />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700">Address</span>
            <textarea name="address" className="mt-1 w-full rounded-lg border border-slate-300 p-2" rows={3} />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700">Personal Essay</span>
            <textarea name="essay" className="mt-1 w-full rounded-lg border border-slate-300 p-2" rows={6} />
          </label>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-sm font-semibold text-slate-700">Passport Upload</span>
              <input name="passport_upload" type="file" className="mt-1 w-full text-sm" />
            </label>

            <label className="block">
              <span className="text-sm font-semibold text-slate-700">Academic Transcript Upload</span>
              <input name="transcript_upload" type="file" className="mt-1 w-full text-sm" />
            </label>
          </div>

          <button
            type="submit"
            className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
          >
            Submit Application
          </button>
        </form>
      </div>
    </div>
  );
}
