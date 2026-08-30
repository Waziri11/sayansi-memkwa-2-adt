/**
 * Synchronize the page-level sign-language video with read-aloud narration.
 * Loaded before the ADT runtime so the stock mutually-exclusive media rules
 * cannot stop the paired narration/video session.
 */
(() => {
  "use strict"

  const NativeAudio = window.Audio
  const nativePause = HTMLMediaElement.prototype.pause
  const nativePlay = HTMLMediaElement.prototype.play
  const timingPromise = fetch("./content/i18n/sw-TZ/sign-language-timings.json")
    .then((response) => (response.ok ? response.json() : {}))
    .catch(() => ({}))

  let narration = null
  let narrationPlaying = false
  let sessionStarted = false
  let currentTiming = null
  let currentTrack = ""

  const sectionId =
    document.querySelector('meta[name="title-id"]')?.getAttribute("content") || ""

  const signVideo = () =>
    document.querySelector('video[src*="/content/i18n/"][src*="/video/"]')

  const isNarration = (audio) => {
    const source = audio.currentSrc || audio.src || ""
    return /\/content\/i18n\/[^/]+\/audio\//.test(source)
  }

  const muteSignVideo = (video) => {
    if (!video) return
    video.defaultMuted = true
    video.muted = true
    video.volume = 0
    video.playsInline = true
  }

  const variantFor = (audio) =>
    /_easy_read(?:[._]|$)/.test(audio.currentSrc || audio.src || "")
      ? "easyRead"
      : "standard"

  const filenameFor = (audio) => {
    const source = audio.currentSrc || audio.src || ""
    try {
      return decodeURIComponent(new URL(source, location.href).pathname.split("/").pop())
    } catch {
      return source.split("/").pop().split("?")[0]
    }
  }

  const applyRate = (audio, video) => {
    if (!audio || !video) return
    const narrationDuration = Number(currentTiming?.[variantFor(audio)]?.total)
    const mediaRatio =
      narrationDuration > 0 && Number.isFinite(video.duration)
        ? video.duration / narrationDuration
        : 1
    video.playbackRate = Math.min(
      16,
      Math.max(0.0625, mediaRatio * (audio.playbackRate || 1)),
    )
  }

  const startTogether = async (audio) => {
    if (!isNarration(audio)) return
    narration = audio
    narrationPlaying = true
    currentTiming ||= (await timingPromise)[sectionId] || null

    const video = signVideo()
    if (!video) return
    muteSignVideo(video)

    const variant = currentTiming?.[variantFor(audio)]
    const filename = filenameFor(audio)
    document.documentElement.dataset.signLanguageNarration = filename
    document.documentElement.dataset.signLanguageVariant = variantFor(audio)
    const track = variant?.tracks?.[filename]
    if (track && Number.isFinite(video.duration)) {
      const intended =
        ((track.offset + (audio.currentTime || 0)) / variant.total) * video.duration
      if (filename !== currentTrack || Math.abs(video.currentTime - intended) > 1.5) {
        video.currentTime = Math.min(video.duration, Math.max(0, intended))
      }
    } else if (!sessionStarted || video.ended) {
      video.currentTime = 0
    }
    if (!sessionStarted || video.ended) {
      sessionStarted = true
    }
    currentTrack = filename
    applyRate(audio, video)
    nativePlay.call(video).catch(() => {})
  }

  const pauseTogether = (audio) => {
    if (audio !== narration || !isNarration(audio) || audio.ended) return
    narrationPlaying = false
    const video = signVideo()
    if (video) {
      nativePause.call(video)
      if (audio.currentTime <= 0.05) {
        video.currentTime = 0
        sessionStarted = false
        currentTrack = ""
      }
    }
  }

  window.Audio = function SynchronizedAudio(...args) {
    const audio = new NativeAudio(...args)
    audio.addEventListener("play", () => startTogether(audio))
    audio.addEventListener("pause", () => pauseTogether(audio))
    audio.addEventListener("ratechange", () => {
      if (audio === narration) applyRate(audio, signVideo())
    })
    return audio
  }
  window.Audio.prototype = NativeAudio.prototype

  // Ignore only the stock runtime's automatic sign-video pause while paired
  // narration is playing. Explicit narration pause still uses nativePause.
  HTMLMediaElement.prototype.pause = function synchronizedPause() {
    if (this === signVideo() && narrationPlaying) return
    return nativePause.call(this)
  }

  // Do not let the sign-video play event switch the stock runtime into its
  // video-only media mode and stop narration.
  window.addEventListener(
    "play",
    (event) => {
      if (event.target === signVideo()) {
        muteSignVideo(event.target)
        event.stopImmediatePropagation()
        if (!narrationPlaying) nativePause.call(event.target)
      }
    },
    true,
  )

  document.addEventListener(
    "volumechange",
    (event) => {
      if (event.target === signVideo()) muteSignVideo(event.target)
    },
    true,
  )

  document.addEventListener(
    "click",
    (event) => {
      const button = event.target.closest?.("button")
      const label = (button?.getAttribute("aria-label") || button?.textContent || "").trim()
      if (label !== "Simamisha" && label !== "Stop") return
      narrationPlaying = false
      sessionStarted = false
      currentTrack = ""
      const video = signVideo()
      if (video) {
        nativePause.call(video)
        video.currentTime = 0
      }
    },
    true,
  )

  new MutationObserver(() => {
    const video = signVideo()
    muteSignVideo(video)
    if (video && narrationPlaying && narration) {
      applyRate(narration, video)
      nativePlay.call(video).catch(() => {})
    }
  }).observe(document.documentElement, { childList: true, subtree: true })

  window.addEventListener("pagehide", () => {
    narrationPlaying = false
    sessionStarted = false
    currentTrack = ""
  })
})()
