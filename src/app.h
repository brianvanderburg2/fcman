// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Header guard
#ifndef __FCMAN_APP_H
#define __FCMAN_APP_H


// Requirements
#include <wx/defs.h>
#include <wx/app.h>
#include <wx/filename.h>
#include <wx/string.h>


class WXDLLIMPEXP_BASE wxCmdLineParser;
class WXDLLIMPEXP_BASE wxConfigBase;

class Options;


// Application class
class Application : public wxApp
{
public:
    // ctor/dtor
    Application();
    virtual ~Application();

    // Creation
    bool OnInit();
    int OnExit();

    // Command line
    void OnInitCmdLine(wxCmdLineParser& parser);
    bool OnCmdLineParsed(wxCmdLineParser& parser);

    // Paths
    wxString GetAppDataPath(const wxString& path = wxEmptyString, wxPathFormat format = wxPATH_NATIVE);
    wxString GetUserDataPath(const wxString& path = wxEmptyString, wxPathFormat format = wxPATH_NATIVE);
    wxString GetPixmapDataPath(const wxString& path = wxEmptyString, wxPathFormat format = wxPATH_NATIVE);
    wxString GetDocPath(const wxString& path = wxEmptyString, wxPathFormat format = wxPATH_NATIVE);
    wxString GetHelpFile();
    wxString GetConfigFile();

    void CreateUserDirs();

    // Config and options
    wxConfigBase* GetConfig() { return m_config; }
    Options& GetOptions() { return *m_options; }

    // Helpers until wxWidgets 3
    #if !wxCHECK_VERSION(3, 0, 0)
        void SetAppDisplayName(const wxString& name) { m_appDispName = name; }
        const wxString& GetAppDisplayName() const { return m_appDispName; }

        void SetVendorDisplayName(const wxString& name) { m_venDispName = name; }
        const wxString& GetVendorDisplayName() const { return m_venDispName; }
    #endif

private:
    // No copy or assign
    Application(const Application& copy);
    Application& operator=(const Application& rhs);

    #if !wxCHECK_VERSION(3, 0, 0)
        wxString m_appDispName;
        wxString m_venDispName;
    #endif

    // Config and options
    wxConfigBase* m_config;
    Options* m_options;

    // Paths
    wxString m_appDataDir;
    wxString m_userDataDir;
    wxString m_docDataDir;
    wxString m_pixmapDataDir;

    // Files to open
    wxString m_file;

};

DECLARE_APP(Application);


#endif // Header guard



