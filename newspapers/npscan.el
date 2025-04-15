(defun npscan-process ()
  (interactive)
  (View-quit)
  (save-excursion
    (set-buffer (get-buffer-create " npscan out"))
    (erase-buffer)
    )
  (let* (pos txtfile
         (indir (dired-get-file-for-visit))
         (dir (file-name-nondirectory indir))
         (stat (call-process "/home/sss/cem/cem/newspapers/chronmd.py" nil " npscan out" t "-n" indir)))
    (if (not (eq stat 0))
        (pop-to-buffer " npscan out")
      (revert-buffer)
      (message (file-name-concat "extra" dir (concat dir ".pdf")))
      (call-process "/usr/bin/xpdf" nil 0 nil (file-name-concat "extra" dir (concat dir ".pdf")))
      (save-excursion
        (set-buffer (get-buffer-create " npscan out"))
        (goto-char (point-min))
        (search-forward "Wrote: ")
        (setq pos (point))
        (end-of-line)
        (setq txtfile (buffer-substring pos (point)))
        (message txtfile)
        (find-file-other-window txtfile)
        )
      ;(find-file-other-window )
      )))

(defun npscan-notcem ()
  (interactive)
  (View-quit)
  (let ((f (dired-get-file-for-visit)))
    (rename-file f (file-name-concat "not-cem" (file-name-nondirectory f))))
  (revert-buffer)
  (message "not CEM!"))

(defun npscan-view ()
  (interactive)
  (let* ((f (dired-get-file-for-visit))
         (textf (file-name-concat f (concat (file-name-nondirectory f) ".text"))))
    (if (not (file-directory-p f))
        (error "File is not a directory.")
      (if (not (file-exists-p f))
          (error "Text file does not exist.")
        (view-file textf)
        (keymap-local-set "[" 'npscan-process)
        (keymap-local-set "]" 'npscan-notcem)
        ))))


(define-minor-mode npscan-mode
  ""
  nil
  " npscan"
  '(([?\r] . npscan-view)))

(defun npscan-dired (dirname &optional switches)
  (interactive (dired-read-dir-and-switches ""))
  (pop-to-buffer-same-window (dired-noselect dirname switches))
  (npscan-mode))

  
