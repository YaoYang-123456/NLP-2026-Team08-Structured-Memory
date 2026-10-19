\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{jos}[2026/06/08 LaTeX style approximating Journal of Software DOCX template]

\LoadClass[twoside,UTF8,fontset=none]{ctexart}

\RequirePackage{ifthen}
\RequirePackage{geometry}
\RequirePackage{amsmath,amsthm,amsfonts,amssymb,bm,mathrsfs}
\RequirePackage{graphicx}
\RequirePackage{xcolor}
\RequirePackage{booktabs,multirow,tabularx,supertabular}
\RequirePackage{algorithm,algorithmic}
\RequirePackage{float}
\RequirePackage{url}
\RequirePackage{fancyhdr}
\RequirePackage{titlesec}
\RequirePackage{caption}
\RequirePackage[superscript,nomove,nospace]{cite}
\RequirePackage{tikz}
\RequirePackage{xeCJKfntef}
\RequirePackage[colorlinks,breaklinks,linkcolor=black,citecolor=black,filecolor=black,urlcolor=black]{hyperref}

\geometry{
  paperwidth=184mm,
  paperheight=260mm,
  left=14.5mm,
  right=14.5mm,
  top=23mm,
  bottom=22mm,
  headheight=14pt,
  headsep=7mm,
  footskip=9mm
}

\makeatletter

% Use TeX Live fonts so this teaching template needs no bundled Windows fonts.
\setmainfont{texgyretermes}[Extension=.otf,UprightFont=*-regular,
  BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic,Ligatures=TeX]
\setCJKmainfont{FandolSong-Regular}[Extension=.otf,
  BoldFont=FandolSong-Bold,ItalicFont=FandolKai-Regular]
\setCJKsansfont{FandolHei-Regular}[Extension=.otf,BoldFont=FandolHei-Bold]
\setCJKmonofont{FandolFang-Regular}[Extension=.otf]
\setCJKfamilyfont{zhsong}{FandolSong-Regular}[Extension=.otf,BoldFont=FandolSong-Bold]
\setCJKfamilyfont{zhhei}{FandolHei-Regular}[Extension=.otf,BoldFont=FandolHei-Bold]
\setCJKfamilyfont{zhfs}{FandolFang-Regular}[Extension=.otf]
\setCJKfamilyfont{zhkai}{FandolKai-Regular}[Extension=.otf]
\setCJKfamilyfont{jossong}{FandolSong-Regular}[Extension=.otf,BoldFont=FandolSong-Bold]
\setCJKfamilyfont{josfang}{FandolFang-Regular}[Extension=.otf]
\setCJKfamilyfont{joskai}{FandolKai-Regular}[Extension=.otf]
\setCJKfamilyfont{joshei}{FandolHei-Regular}[Extension=.otf,BoldFont=FandolHei-Bold]
\newfontfamily\jossonglatin{texgyretermes-regular.otf}
\newfontfamily\joskailatin{texgyretermes-italic.otf}
\newcommand{\jossongti}{\CJKfamily{jossong}}
\newcommand{\josfangsong}{\CJKfamily{josfang}}
\newcommand{\joskaiti}{\CJKfamily{joskai}}
\newcommand{\josheiti}{\CJKfamily{joshei}}

\renewcommand\normalsize{%
  \@setfontsize\normalsize{9pt}{14.25pt}%
  \abovedisplayskip 8pt plus 2pt minus 4pt%
  \belowdisplayskip \abovedisplayskip%
  \abovedisplayshortskip 0pt plus 2pt%
  \belowdisplayshortskip 4pt plus 2pt minus 2pt%
}
\normalsize
\setlength{\parindent}{2em}
\setlength{\parskip}{0pt}
\renewcommand{\baselinestretch}{1}
\renewcommand{\arraystretch}{1.15}
\urlstyle{same}

\newcommand{\jos@journal}{软件学报}
\newcommand{\jos@enjournal}{Journal of Software}
\newcommand{\jos@issn}{1000-9825}
\newcommand{\jos@coden}{RUXUEW}
\newcommand{\jos@email}{jos@iscas.ac.cn}
\newcommand{\jos@website}{http://www.jos.org.cn}
\newcommand{\jos@tel}{+86-10-62562563}
\newcommand{\jos@copyright}{\copyright 中国科学院软件研究所版权所有}

\def\@Year{2026}
\def\@Vol{00}
\def\@No{0}
\def\@Month{Month}
\def\@BeginPage{1}
\def\@DOI{10.13328/j.cnki.jos.000000}
\def\@CLC{TODO}
\def\@ArticleURL{http://www.jos.org.cn/1000-9825/0000.htm}
\def\@ArticleType{}
\def\@Foundation{}
\def\@ReceiveDate{}
\def\@ReviseDate{}
\def\@AcceptDate{}
\def\@OnlineDate{}
\def\@AuthorMark{}
\def\@AuthorCitation{}
\def\@enAuthorCitation{}
\def\@comment{}
\def\@encomment{}
\def\@ReferenceName{References:}

\newcommand{\Year}[1]{\def\@Year{#1}}
\newcommand{\Vol}[1]{\def\@Vol{#1}}
\newcommand{\No}[1]{\def\@No{#1}}
\newcommand{\Month}[1]{\def\@Month{#1}}
\newcommand{\BeginPage}[1]{\def\@BeginPage{#1}}
\newcommand{\DOI}[1]{\def\@DOI{#1}}
\newcommand{\CLC}[1]{\def\@CLC{#1}}
\newcommand{\ArticleURL}[1]{\def\@ArticleURL{#1}}
\newcommand{\ArticleType}[1]{\def\@ArticleType{#1}}
\newcommand{\Foundation}[1]{\def\@Foundation{#1}}
\newcommand{\ReceiveDate}[1]{\def\@ReceiveDate{#1}}
\newcommand{\ReviseDate}[1]{\def\@ReviseDate{#1}}
\newcommand{\AcceptDate}[1]{\def\@AcceptDate{#1}}
\newcommand{\OnlineDate}[1]{\def\@OnlineDate{#1}}
\newcommand{\AuthorMark}[1]{\def\@AuthorMark{#1}}
\newcommand{\AuthorCitation}[1]{\def\@AuthorCitation{#1}}
\newcommand{\enAuthorCitation}[1]{\def\@enAuthorCitation{#1}}
\newcommand{\comment}[1]{\def\@comment{#1}}
\newcommand{\encomment}[1]{\def\@encomment{#1}}
\newcommand{\ReferenceName}[1]{\def\@ReferenceName{#1}}
\newcommand{\SpecialTopic}[1]{}
\newcommand{\Luntan}[1]{}

\def\@title{}
\def\@titlehead{}
\def\@entitle{}
\def\@entitlehead{}
\renewcommand{\title}[2]{\def\@title{#1}\def\@titlehead{#2}}
\newcommand{\entitle}[2]{\def\@entitle{#1}\def\@entitlehead{#2}}

\def\@author{}
\def\@enauthor{}
\def\jos@authorsep{}
\def\jos@enauthorsep{}
\def\@corrauthor{}
\def\@corremail{}
\newcommand{\jos@superscript}[1]{\textsuperscript{#1}}
\renewcommand*{\author}[4][]{%
  \def\jos@affix{#1}%
  \ifx\@author\@empty
    \ifx\jos@affix\@empty
      \g@addto@macro\@author{#2}%
      \g@addto@macro\@enauthor{#3}%
    \else
      \g@addto@macro\@author{#2\jos@superscript{#1}}%
      \g@addto@macro\@enauthor{#3\jos@superscript{#1}}%
    \fi
  \else
    \g@addto@macro\@author{,\quad}%
    \g@addto@macro\@enauthor{,\quad}%
    \ifx\jos@affix\@empty
      \g@addto@macro\@author{#2}%
      \g@addto@macro\@enauthor{#3}%
    \else
      \g@addto@macro\@author{#2\jos@superscript{#1}}%
      \g@addto@macro\@enauthor{#3\jos@superscript{#1}}%
    \fi
  \fi
  \def\jos@emailtmp{#4}%
  \ifx\jos@emailtmp\@empty\else
    \gdef\@corrauthor{#2}%
    \gdef\@corremail{#4}%
  \fi
}

\def\@address{}
\def\@enaddress{}
\newcommand*{\address}[3][]{%
  \def\jos@addrnote{#1}%
  \ifx\@address\@empty
    \gdef\@address{\ifx\jos@addrnote\@empty\else\jos@superscript{#1}\fi(#2)}%
    \gdef\@enaddress{\ifx\jos@addrnote\@empty\else\jos@superscript{#1}\fi(#3)}%
  \else
    \g@addto@macro\@address{\\\ifx\jos@addrnote\@empty\else\jos@superscript{#1}\fi(#2)}%
    \g@addto@macro\@enaddress{\\\ifx\jos@addrnote\@empty\else\jos@superscript{#1}\fi(#3)}%
  \fi
}

\def\@abstract{}
\def\@enabstract{}
\def\@keywords{}
\def\@enkeywords{}
\renewcommand{\abstract}[1]{\def\@abstract{#1}}
\newcommand{\enabstract}[1]{\def\@enabstract{#1}}
\newcommand{\keywords}[1]{\def\@keywords{#1}}
\newcommand{\enkeywords}[1]{\def\@enkeywords{#1}}

\newcommand{\jos@small}{\jossongti\fontsize{7.5pt}{9pt}\selectfont}
\newcommand{\jos@eight}{\jossongti\fontsize{8pt}{10pt}\selectfont}
\newcommand{\jos@affilfont}{\jossongti\fontsize{8pt}{12pt}\selectfont}
\newcommand{\jos@enaffilfont}{\rmfamily\jossongti\fontsize{7.5pt}{12pt}\selectfont}
\newcommand{\jos@authorfont}{\josfangsong\fontsize{12pt}{14pt}\selectfont}
\newcommand{\jos@cnabsfont}{\joskaiti\fontsize{9pt}{14.25pt}\selectfont}
\newcommand{\jos@enabs}{\rmfamily\joskaiti\fontsize{7.5pt}{11.7pt}\selectfont}
\newcommand{\jos@citefont}{\rmfamily\jossongti\fontsize{8pt}{12pt}\selectfont}
\newcommand{\jos@headerfont}{\joskaiti\fontsize{7.5pt}{9pt}\selectfont}
\newcommand{\jos@footnotefont}{\normalfont\rmfamily\jossongti\fontsize{7.5pt}{10.5pt}\selectfont}
\newcommand{\jos@refheadingfont}{\normalfont\rmfamily\josheiti\bfseries\fontsize{9pt}{14.25pt}\selectfont}
\newcommand{\jos@reffont}{\normalfont\rmfamily\jossongti\fontsize{7.5pt}{13pt}\selectfont}
\newcommand{\jos@authorbiofont}{\normalfont\rmfamily\jossongti\fontsize{7.5pt}{12pt}\selectfont}
\newcommand{\jos@authorbionamefont}{\normalfont\rmfamily\josheiti\bfseries\fontsize{7.5pt}{12pt}\selectfont}
\newcommand{\jos@condense}[1]{\scalebox{0.66}[1]{#1}}

\newcommand{\jos@topmatter}{%
  \noindent{\jos@small
  \begin{tabularx}{\linewidth}{@{}Xr@{}}
    \jos@journal ISSN \jos@issn, CODEN \jos@coden & E-mail: \jos@email\\
    \textit{\jos@enjournal}, [doi: \@DOI] & \jos@website\\
    \jos@copyright. & Tel: \jos@tel
  \end{tabularx}}\par
}

\ExplSyntaxOn
\cs_new_protected:Npn \jos_highlight_text:n #1
  {
    \xeCJK_ulem_group_begin:
      \markoverwith { \textcolor { black!6 } { \rule[-0.35ex]{0.12em}{1.7ex} } }
      \ULon {#1}
  }
\cs_new_protected:cpn { jos@highlighttext } #1
  { \jos_highlight_text:n {#1} }
\ExplSyntaxOff
\newcommand{\jos@citationbox}[2]{%
  \begingroup
    \protected@edef\jos@citationtext{#1: #2}%
    \noindent\jos@citefont\expandafter\jos@highlighttext\expandafter{\jos@citationtext}\par
  \endgroup
}

\renewcommand\footnoterule{%
  \kern -3pt%
  \hrule width 0.33\textwidth height 0.4pt%
  \kern 5pt%
}
\long\def\@makefntext#1{%
  \jos@footnotefont
  \setlength{\parindent}{11.6pt}%
  \noindent\hbox to 11.6pt{\@thefnmark\hfil}#1%
}
\newcommand{\jos@foundationmark}{%
  \ifx\@Foundation\@empty\else
    \textsuperscript{\normalfont\fontsize{10.5pt}{10.5pt}\selectfont *}%
  \fi
}
\newcommand{\jos@foundationfootnote}{%
  \ifx\@Foundation\@empty\else
    \begingroup
      \renewcommand{\thefootnote}{\fnsymbol{footnote}}%
      \footnotetext[1]{%
        基金项目: \@Foundation
        \ifx\@ReceiveDate\@empty\else
          \\收稿时间: \@ReceiveDate; 修改时间: \@ReviseDate; 采用时间: \@AcceptDate
        \fi
      }%
    \endgroup
  \fi
}

\renewcommand{\maketitle}{%
  \setcounter{page}{\@BeginPage}%
  \thispagestyle{plain}%
  \vspace*{-17mm}%
  \jos@topmatter
  \vspace{16pt}
  {\raggedright\josheiti\fontsize{14pt}{17pt}\selectfont \@title\jos@foundationmark\par}
  \jos@foundationfootnote
  \vspace{8pt}
  {\raggedright\jos@authorfont\jos@condense{\@author}\par}
  \vspace{12pt}
  {\raggedright\jos@affilfont
    \hangindent=5.8pt\hangafter=1 \@address\par
    \ifx\@corremail\@empty\else
      \hangindent=5.8pt\hangafter=1 通讯作者: \@corrauthor, E-mail: \@corremail\par
    \fi}
  \vspace{12pt}
  \ifx\@abstract\@empty\else
    {\jos@cnabsfont
      \noindent{\josheiti 摘\quad 要:}\@abstract\par
      \noindent{\josheiti 关键词:} \@keywords\par}
  \fi
  \vspace{3pt}
  {\noindent\fontsize{9pt}{11pt}\selectfont 中图法分类号: \@CLC\par}
  \vspace{11pt}
  \jos@citationbox{中文引用格式}{\@AuthorCitation. \@title. 软件学报,\@Year,\@Vol(\@No). \@ArticleURL}
  \vspace{2.85pt}
  \jos@citationbox{英文引用格式}{\@enAuthorCitation. \@entitle. Ruan Jian Xue Bao/Journal of Software, \@Year\ (in Chinese). \@ArticleURL}
  \vspace{5pt}
  {\raggedright\josheiti\bfseries\fontsize{10.5pt}{13pt}\selectfont \@entitle\par}
  \vspace{5pt}
  {\raggedright\jossongti\fontsize{9pt}{11pt}\selectfont \@enauthor\par}
  \vspace{5pt}
  {\raggedright\jos@enaffilfont\hangindent=5.15pt\hangafter=1 \@enaddress\par}
  \ifx\@enabstract\@empty\else
    \vspace{7.1pt}
    {\jos@enabs
      \noindent{\bfseries Abstract:}\quad \@enabstract\par
      \noindent{\bfseries Key words:}\quad \@enkeywords\par}
  \fi
  \vspace{8pt}
}

\newcommand{\makeentitle}{}

\pagestyle{fancy}
\fancyhf{}
\setlength{\headwidth}{\textwidth}
\fancyhead[LO]{\jos@headerfont\thepage}
\fancyhead[RO]{\jos@headerfont{\normalfont\itshape Journal of Software}\ {\joskaiti 软件学报}\ Vol.\@Vol, No.\@No, \@Month\ \@Year}
\fancyhead[LE]{\jos@headerfont\@AuthorMark\ 等:\@titlehead}
\fancyhead[RE]{\jos@headerfont\thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\fancypagestyle{plain}{%
  \fancyhf{}%
  \renewcommand{\headrulewidth}{0pt}%
  \renewcommand{\footrulewidth}{0pt}%
}

\setcounter{secnumdepth}{3}
\titleformat{\section}{\josheiti\fontsize{10.5pt}{14pt}\selectfont}{\makebox[15.9pt][l]{\normalfont\rmfamily\bfseries\fontsize{10.5pt}{14pt}\selectfont\thesection}}{0pt}{}
\titlespacing{\section}{0pt}{8pt plus 2pt minus 1pt}{8pt plus 1pt minus 1pt}
\titleformat{\subsection}{\normalfont\josheiti\fontsize{9pt}{14.25pt}\selectfont}{\makebox[20.7pt][l]{\normalfont\rmfamily\bfseries\fontsize{9pt}{14.25pt}\selectfont\thesubsection}}{0pt}{}
\titlespacing{\subsection}{0pt}{3.55pt plus 1pt minus 0.5pt}{3.55pt plus 0.5pt minus 0.5pt}
\titleformat{\subsubsection}{\josheiti\normalsize}{\thesubsubsection}{0.6em}{}
\titlespacing{\subsubsection}{0pt}{4pt plus 1pt minus 1pt}{4pt plus 1pt minus 1pt}
\titleformat{\paragraph}[runin]{\normalfont\normalsize\bfseries}{\theparagraph}{0pt}{}
\titlespacing*{\paragraph}{0pt}{3pt plus 1pt minus 1pt}{0.5em}

\DeclareCaptionFont{joscaption}{\rmfamily\jossongti\fontsize{9pt}{12pt}\selectfont}
\DeclareCaptionFont{jostablelabel}{\rmfamily\josheiti\bfseries\fontsize{9pt}{12pt}\selectfont}
\DeclareCaptionLabelFormat{joslabel}{#1~#2}
\captionsetup{font=joscaption,labelfont=joscaption,labelformat=joslabel,labelsep=quad,justification=centering,singlelinecheck=false}
\captionsetup[figure]{name=图,labelfont=joscaption,aboveskip=3pt,belowskip=7pt}
\captionsetup[table]{name=表,labelfont=jostablelabel,aboveskip=3pt,belowskip=7pt}
\captionsetup[algorithm]{name=算法,font=joscaption,labelfont=joscaption}
\floatname{algorithm}{算法}
\setlength{\floatsep}{10pt plus 2pt minus 2pt}
\setlength{\textfloatsep}{12pt plus 2pt minus 2pt}
\setlength{\intextsep}{10pt plus 2pt minus 2pt}
\setlength{\aboverulesep}{0pt}
\setlength{\belowrulesep}{0pt}

\newcommand*{\cnenfigcaption}[2]{\caption{#1}}
\newcommand*{\cnentablecaption}[2]{\caption{#1}}
\renewcommand{\@citess}[1]{\mbox{$\m@th^{\hbox{\OverciteFont{\citeleft#1\citeright}}}$}}
\newcommand{\upcite}[1]{\cite{#1}}
\providecommand{\citedash}{\hbox{$\sim$}\penalty\@m}

\renewcommand{\refname}{\@ReferenceName}
\def\@biblabel#1{[#1]}
\newcommand{\jos@refheading}{%
  \par\addvspace{14pt}%
  {\noindent\jos@refheadingfont \refname\par}%
  \nobreak
}
\renewenvironment{thebibliography}[1]{%
  \jos@refheading
  \addcontentsline{toc}{section}{\refname}%
  \jos@reffont
  \list{\@biblabel{\@arabic\c@enumiv}}{%
    \settowidth\labelwidth{\@biblabel{#1}}%
    \leftmargin=20.9pt
    \labelsep\leftmargin
    \advance\labelsep-\labelwidth
    \itemsep=0pt
    \parsep=0pt
    \partopsep=0pt
    \topsep=0pt
    \listparindent=0pt
    \itemindent=0pt
    \usecounter{enumiv}%
    \let\p@enumiv\@empty
    \renewcommand\theenumiv{\@arabic\c@enumiv}}%
  \jos@reffont
  \sloppy
  \clubpenalty4000
  \@clubpenalty \clubpenalty
  \widowpenalty4000
  \sfcode`\.\@m
}{%
  \def\@noitemerr{\@latex@warning{Empty `thebibliography' environment}}%
  \endlist
}

\renewenvironment{itemize}{%
  \begin{list}{$\bullet$}{%
    \labelwidth=1em
    \labelsep=0.5em
    \leftmargin=2em
    \parsep=0pt
    \itemsep=0pt
    \topsep=2pt}}{\end{list}}

\newlength{\jos@authorbiophotowidth}
\newlength{\jos@authorbiophotoheight}
\newlength{\jos@authorbiophotohalfwidth}
\newlength{\jos@authorbiophotohalfheight}
\newlength{\jos@authorbiophotocol}
\newlength{\jos@authorbiotextcol}
\newlength{\jos@authorbiogap}
\setlength{\jos@authorbiophotowidth}{16.8mm}
\setlength{\jos@authorbiophotoheight}{22.2mm}
\setlength{\jos@authorbiophotohalfwidth}{8.4mm}
\setlength{\jos@authorbiophotohalfheight}{11.1mm}
\setlength{\jos@authorbiophotocol}{20.2mm}
\setlength{\jos@authorbiotextcol}{51.6mm}
\setlength{\jos@authorbiogap}{7.7mm}

\newcommand{\jos@authorbioimage}[1]{%
  \begin{tikzpicture}[baseline=(josauthorbioimage.center)]
    \path[use as bounding box] (0pt,0pt) rectangle
      (\jos@authorbiophotowidth,\jos@authorbiophotoheight);
    \clip (0pt,0pt) rectangle
      (\jos@authorbiophotowidth,\jos@authorbiophotoheight);
    \node[inner sep=0pt,anchor=center] (josauthorbioimage)
      at (\jos@authorbiophotohalfwidth,\jos@authorbiophotohalfheight)
      {\includegraphics[height=\jos@authorbiophotoheight]{#1}};
  \end{tikzpicture}%
}
\newcommand{\josauthorbio}[3]{%
  \begin{minipage}[t][24.2mm][t]{\jos@authorbiophotocol}
    \vspace*{0pt}\centering\jos@authorbioimage{#1}%
  \end{minipage}%
  &%
  \begin{minipage}[t][24.2mm][t]{\jos@authorbiotextcol}
    \vspace*{0pt}%
    \raggedright\jos@authorbiofont
    {\jos@authorbionamefont #2}#3\par
  \end{minipage}%
}
\newcommand{\josauthorbioempty}{%
  \begin{minipage}[t][24.2mm][t]{\jos@authorbiophotocol}\strut\end{minipage}%
  &%
  \begin{minipage}[t][24.2mm][t]{\jos@authorbiotextcol}\strut\end{minipage}%
}
\newenvironment{josauthorbios}{%
  \par\addvspace{12pt}%
  \begingroup
  \centering
  \jos@authorbiofont
  \setlength{\tabcolsep}{0pt}%
  \renewcommand{\arraystretch}{1}%
  \begin{tabular}{@{}p{\jos@authorbiophotocol}@{}p{\jos@authorbiotextcol}@{\hspace{\jos@authorbiogap}}p{\jos@authorbiophotocol}@{}p{\jos@authorbiotextcol}@{}}
}{%
  \end{tabular}%
  \par
  \endgroup
}

\newtheoremstyle{josdefinition}
  {2pt}{2pt}{\normalfont}{2em}{\bfseries\josheiti}{}{0.6em}{}
\theoremstyle{josdefinition}
\newtheorem{definition}{定义}
\newtheorem{theorem}{定理}
\newtheorem{lemma}{引理}
\newtheorem{corollary}{推论}
\newtheorem{axiom}{公理}
\newtheorem{propsition}{命题}
\newtheorem{example}{例}
\newtheorem{exercise}{习题}
\newtheorem{solution}{解}
\newtheorem{notation}{注}
\newtheorem{assumption}{假设}
\newtheorem{remark}{注释}
\newtheorem{property}{性质}

\newcommand{\set}[1]{\ensuremath{\left\{ #1 \right\}}}
\newcommand{\Set}[2]{\ensuremath{\left\{ #1 \left| \right. #2 \right\}}}
\newcommand{\abs}[1]{\ensuremath{\left| #1 \right|}}
\newcommand{\map}[3]{\ensuremath{#1 : #2 \rightarrow #3}}
\newcommand{\C}[1]{\ensuremath{\mathcal{#1}}}
\newcommand{\restrict}[2]{\ensuremath{#1 \left|_{#2}\right.}}
\newcommand{\NN}{\mathbb{N}^0}
\newcommand{\PN}{\mathbb{N}}
\newcommand{\syn}{\mathbf{S}}
\newcommand{\Syn}{\mathbf{M}}
\allowdisplaybreaks
\setlength{\arraycolsep}{2pt}

\makeatother
\endinput
